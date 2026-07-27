# B-S01 - Chargement des donnees A8

- **Experience :** B - Dynamique d'une voiture
- **Scenario :** B-S01
- **Statut :** valide
- **Date :** 2026-07-26T19:19:34Z
- **Objectif :** charger et valider les trois documents `AutomationRawVehicleData` v0.1 produits par A8.

## Synthese

- Documents trouves : 3
- Documents valides : 3
- Documents en echec : 0
- Valeurs brutes de graphes chargees : 13304

## Resultats par voiture

| Voiture | Contrat | Champs | Graphes disponibles | Graphes bruts | Series | Valeurs | Avertissements |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| AIXAM - Coupe GTI | valide | 73 / 73 | 10 | 3 | 24 | 2607 | Automation version was not exposed by Lua data |
| PCM - Magmort - Carcharhini Recif | valide | 73 / 73 | 10 | 3 | 24 | 4768 | Automation version was not exposed by Lua data |
| QFC55 - Magmort - Carcharhini RCZ | valide | 73 / 73 | 10 | 3 | 24 | 5929 | Automation version was not exposed by Lua data |

## Graphes requis

| Voiture | AccelerationToTopSpeed | Braking | BrakingVGrip |
| --- | --- | --- | --- |
| AIXAM - Coupe GTI | oui | oui | oui |
| PCM - Magmort - Carcharhini Recif | oui | oui | oui |
| QFC55 - Magmort - Carcharhini RCZ | oui | oui | oui |

## Observations

- Les trois voitures A8 sont chargeables par le prototype B.
- Le validateur A8 existant est reutilise comme garde-fou de contrat.
- Les graphes `AccelerationToTopSpeed`, `Braking` et `BrakingVGrip` sont presents pour les trois voitures.
- Les avertissements restants concernent l'absence de version Automation exposee par les donnees Lua.

## Decision

B-S01 est valide. Le prochain jalon peut construire les interpolateures des courbes longitudinales pour B-S02 et B-S03.

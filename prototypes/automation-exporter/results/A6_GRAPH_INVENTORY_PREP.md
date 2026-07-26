# A6 — Préparation inventaire GraphData

- **Expérience :** A — Extraction Automation
- **Statut :** remplacé par le résultat validé `A6_GRAPH_INVENTORY_RESULT.md`
- **Date :** 2026-07-26
- **Exporter préparé :** `0.1.9-a6-graph-inventory`

## Objectif

Inventorier les graphes calculés déjà exposés par Automation sous :

```text
CarInfo.TrimInfo.Results.GraphData
```

L'objectif n'est pas encore de choisir le modèle physique de simulation. A6 doit d'abord révéler quelles courbes Automation fournit, sous quelle forme, et si elles sont stables.

## Fichier ajouté

```text
automation-lap-graph-inventory.json
```

Le fichier contient :

- version de schéma ;
- version d'exporteur ;
- horodatage UTC injecté côté C++ ;
- chemin racine sondé ;
- présence et type Lua de `GraphData` ;
- liste des entrées nommées ;
- pour chaque entrée : type Lua, nombre d'entrées, compteurs de types, aperçu des premières et dernières valeurs numériques, min/max si série numérique séquentielle ;
- enfants nommés jusqu'à une profondeur bornée.

## Bornes de sécurité

- maximum 64 enfants nommés par noeud ;
- maximum 5 premières valeurs numériques ;
- maximum 5 dernières valeurs numériques ;
- pas de dump récursif non borné ;
- pas d'appel aux fonctions documentées tant que l'absence de `pcall` n'est pas contournée.

## Validateur

Le validateur indépendant est :

```text
prototypes/automation-exporter/tools/validate_graph_inventory.py
```

Commande :

```powershell
python prototypes\automation-exporter\tools\validate_graph_inventory.py `
  "C:\chemin\vers\automation-lap-graph-inventory.json"
```

## Données attendues après export réel

Pour commencer A6, exporter au moins l'AIXAM Coupe GTI avec la DLL `0.1.9-a6-graph-inventory`, puis fournir :

- `automation-lap-vehicle.json` ;
- `automation-lap-field-inventory.json` ;
- `automation-lap-graph-inventory.json`.

Si l'export AIXAM valide le contrat, refaire ensuite les trois voitures contrastées.

## Points à examiner

- noms des graphes disponibles ;
- présence de `BrakingVGrip` ;
- sous-courbes `FrontBrakeForce`, `FrontBrakeGrip`, `RearBrakeForce`, `RearBrakeGrip` ;
- courbes moteur, puissance, couple, accélération, freinage ou vitesse si exposées ;
- longueur des séries ;
- min/max ;
- stabilité entre exports ;
- hypothèse d'axe, probablement vitesse pour certains graphes, à confirmer.

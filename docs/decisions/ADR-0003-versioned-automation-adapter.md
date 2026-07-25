# ADR-0003 — Adaptateur versionné pour les données Automation

- **Statut :** proposé
- **Date :** 25 juillet 2026

## Contexte

Automation constitue la source d’entrée des voitures, mais ses structures, unités et champs ne correspondent pas nécessairement aux besoins du modèle physique interne. Ils peuvent également évoluer avec les versions du jeu ou de l’exporteur.

Utiliser directement les données exportées dans la simulation créerait une dépendance forte et rendrait les replays ou sauvegardes historiques fragiles.

## Décision

Le pipeline comprendra trois niveaux :

1. `AutomationRawVehicleData`, fidèle à l’export ;
2. un convertisseur et un rapport de validation ;
3. `VehicleDefinition`, stable et indépendante d’Automation.

Chaque champ interne conservera une provenance : exporté, calculé, valeur par défaut ou calibration manuelle. Les fichiers enregistreront au minimum la version d’Automation, la version de l’exporteur, la version du schéma et celle du modèle de conversion.

Les calculs internes utiliseront les unités SI.

## Conséquences positives

- protection du cœur contre les changements externes ;
- réimport et migration contrôlés ;
- valeurs manquantes visibles ;
- comparaison des versions possible ;
- voitures historiques conservables dans un format interne stable.

## Coûts et contraintes

- développement et maintenance d’un adaptateur ;
- dictionnaire des champs indispensable ;
- paramètres dérivés à calibrer ;
- tests de compatibilité pour chaque version prise en charge.

## Alternatives écartées

- lecture directe des fichiers Automation par la physique ;
- remplacement silencieux des valeurs manquantes ;
- format interne identique au format d’export externe.

# Rapport consolidé de faisabilité

- **Statut :** en cours
- **Version :** 0.2
- **Phase :** Phase 1
- **Ticket directeur :** #2
- **Date d’ouverture :** 25 juillet 2026

Ce document est le livrable final de la Phase 1. Il doit rester synthétique : les protocoles, journaux, données et mesures détaillées appartiennent aux rapports d’expérience.

## 1. Résumé exécutif

> À compléter à mesure des expériences.

### Décision générale

- **Décision :** non prise
- **Niveau de confiance :** non évalué
- **Recommandation :** terminer au minimum les expériences A, B, C et E avant toute décision sur le code de production. L’expérience G doit être conclue avant de retenir UR2D2 comme outil officiel de création de circuits.

## 2. Tableau des décisions

| Expérience | Question | Conclusion | Niveau de confiance | Risque résiduel principal |
|---|---|---|---|---|
| A — Extraction Automation | Les données nécessaires sont-elles exportables et stables ? | Validée avec réserves | Moyen | Unités Automation encore partielles |
| B — Dynamique d’une voiture | Un modèle 2D commun produit-il des différences plausibles ? | Validée avec réserves | Moyen | Direction encore calibrable, unités latérales inconnues |
| C — Tour autonome et circuit minimal | Le contrôleur peut-il rouler sans script par virage avec un contrat de circuit minimal ? | En attente | — | Modèle de circuit surdimensionné ou insuffisant pour le contrôle |
| D — Trafic et dépassement | Les interactions peuvent-elles être crédibles et réglables ? | En attente | — | Collisions, immobilisme ou comportement trop déterministe |
| E — Replay minimal | Le replay hybride est-il autonome et navigable ? | En attente | — | Taille des fichiers et compatibilité de version |
| F — Charge et accélération | La cible de voitures et l’exécution accélérée sont-elles viables ? | En attente | — | Coût combiné physique, perception, IA et enregistrement |
| G — Import UR2D2 | Les fichiers UR2D2 peuvent-ils reconstruire le modèle minimal validé en C ? | En attente | — | Format opaque, échelle ambiguë ou informations insuffisantes |

Conclusions autorisées : `validée`, `validée avec réserves`, `à modifier`, `non viable`.

## 3. Paramètres candidats retenus

| Domaine | Paramètre | Valeur candidate | Origine | Statut |
|---|---|---:|---|---|
| Simulation | Pas de temps physique | `1/60 s` candidat, `1/120 s` référence de mesure | Expérience B-S05 | Candidat |
| Circuit | Schéma minimal `TrackDefinition` | À définir | Expérience C | En attente |
| Circuit | Tolérances de fermeture et continuité | À mesurer | Expérience C | En attente |
| Circuit | Transformation UR2D2 vers unités SI | À déterminer | Expérience G | En attente |
| Contrôle IA | Fréquence de commande | À mesurer | Expérience C | En attente |
| Perception | Fréquence de mise à jour | À mesurer | Expérience D | En attente |
| Replay | Fréquence des images-clés | À mesurer | Expérience E | En attente |
| Replay | Fréquence de télémétrie | À mesurer | Expérience E | En attente |
| Performance | Nombre cible de voitures | 12 à 20 | Plan général | À confirmer |

## 4. Résultats par expérience

### A — Extraction Automation

- **Ticket :** #3
- **Conclusion :** validée avec réserves pour l'entrée de B
- **Preuves principales :** exports trois voitures, validation de répétabilité, inventaire des graphes, séries brutes A7, contrat unifié A8 `AutomationRawVehicleData` v0.1
- **Données manquantes :** unités exactes de certaines courbes Automation, usage physique final des graphes de freinage et de grip
- **Impact sur ADR-0003 :** le format brut versionné devient l'entrée candidate de l'adaptateur Automation

### B — Dynamique d’une voiture

- **Ticket :** #4
- **Conclusion :** validée avec réserves
- **Modèle testé :** état 2D minimal vitesse / position / cap, alimenté par les courbes Automation A9
- **Écarts mesurés :** B-S05 stable aux pas `1/30 s`, `1/60 s` et `1/120 s` ; B-S06 conserve les différences inter-voitures sur toutes les métriques consolidées
- **Paramètres dérivés nécessaires :** normalisation de direction, loi latérale calibrable, unités finales des graphes `LowSpeedSteering` et `HighSpeedSteering`

### C — Tour autonome et modèle minimal de circuit

- **Ticket :** #5
- **Conclusion :** en attente
- **Contrôleur testé :** à compléter
- **Schéma minimal retenu :** à compléter
- **Invariants et tolérances :** à compléter
- **Régularité :** à compléter
- **Différenciation des pilotes :** à compléter
- **Données obligatoires pour un importeur :** à compléter

### D — Trafic et dépassement

- **Ticket :** #6
- **Conclusion :** en attente
- **Taux de contact :** à compléter
- **Taux de dépassement :** à compléter
- **Cas d’immobilisme :** à compléter

### E — Replay minimal

- **Ticket :** #7
- **Conclusion :** en attente
- **Format testé :** à compléter
- **Taille et débit :** à compléter
- **Compatibilité :** à compléter

### F — Charge et accélération

- **Ticket :** #8
- **Conclusion :** en attente
- **Machine de référence :** à compléter
- **Temps réel :** à compléter
- **Mode sans rendu :** à compléter
- **Goulets d’étranglement :** à compléter

### G — Import du modèle minimal depuis UR2D2

- **Ticket :** #10
- **Conclusion :** en attente
- **Versions UR2D2 testées :** à compléter
- **Fichiers et structures identifiés :** à compléter
- **Champs du contrat reconstruits :** à compléter
- **Transformation de coordonnées :** à compléter
- **Interventions manuelles nécessaires :** à compléter
- **Décision d’adoption d’UR2D2 :** à compléter

## 5. Risques résiduels

| Risque | Probabilité | Impact | Preuve disponible | Réponse proposée |
|---|---|---|---|---|
| Données Automation insuffisantes | Moyenne | Élevé | Expérience A8 | Paramètres dérivés, usage des courbes Automation et calibration documentée pendant B |
| Modèle physique trop coûteux | À évaluer | Élevé | Expériences B et F | Simplification guidée par mesure |
| Modèle de circuit inadapté au contrôle | À évaluer | Élevé | Expérience C | Définition pilotée par les usages et invariants testés |
| IA peu crédible en trafic | À évaluer | Élevé | Expériences C et D | Architecture en couches et scénarios statistiques |
| Replay trop volumineux | À évaluer | Moyen | Expérience E | Fréquences et compression adaptées |
| Import UR2D2 incomplet ou fragile | À évaluer | Moyen à élevé | Expérience G | Adaptateur versionné et solution de repli indépendante |
| Dépendance excessive à Unity | Faible par conception | Élevé | ADR-0001 | Tests sans rendu et frontières de dépendance |

## 6. Changements requis

### Plan général

- Aucun changement de périmètre produit identifié à ce jour.
- La Phase 1 contient désormais une expérience supplémentaire dédiée à l’import UR2D2.

### Architecture

- Confirmer après C la séparation `TrackDefinition` / données runtime dérivées.
- Prévoir après G une frontière `UR2D2RawTrackData` → convertisseur → `TrackDefinition` si l’import est viable.

### ADR

- ADR-0001 : à confirmer après B et F.
- ADR-0002 : à confirmer après E.
- ADR-0003 : à confirmer après A.
- ADR relatif au format de circuit et aux importeurs externes : à envisager après C et G.

## 7. Décision de sortie

La décision finale doit sélectionner une option :

- **Go** : les risques majeurs sont suffisamment réduits pour développer le vertical slice ;
- **Go avec réserves** : développement autorisé avec contraintes et travaux de réduction de risque intégrés ;
- **Rework** : une ou plusieurs expériences doivent être reprises avant le code de production ;
- **No-Go** : le concept ou l’architecture doit être profondément revu.

La décision générale de passage au vertical slice peut être distincte de la décision d’utiliser UR2D2. Un résultat négatif de G peut conduire à un `Go` pour le projet avec une autre chaîne de création de circuits.

### Décision

> Non prise.

### Conditions éventuelles

> À compléter.

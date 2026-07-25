# Rapport consolidé de faisabilité

- **Statut :** en cours
- **Version :** 0.1
- **Phase :** Phase 1
- **Ticket directeur :** #2
- **Date d’ouverture :** 25 juillet 2026

Ce document est le livrable final de la Phase 1. Il doit rester synthétique : les protocoles, journaux, données et mesures détaillées appartiennent aux rapports d’expérience.

## 1. Résumé exécutif

> À compléter à mesure des expériences.

### Décision générale

- **Décision :** non prise
- **Niveau de confiance :** non évalué
- **Recommandation :** terminer au minimum les expériences A, B, C et E avant toute décision sur le code de production.

## 2. Tableau des décisions

| Expérience | Question | Conclusion | Niveau de confiance | Risque résiduel principal |
|---|---|---|---|---|
| A — Extraction Automation | Les données nécessaires sont-elles exportables et stables ? | En attente | — | Compatibilité réelle du SDK avec la version installée |
| B — Dynamique d’une voiture | Un modèle 2D commun produit-il des différences plausibles ? | En attente | — | Paramètres physiques absents ou difficiles à calibrer |
| C — Tour autonome | Le contrôleur peut-il rouler sans script par virage ? | En attente | — | Instabilité du contrôle aux limites d’adhérence |
| D — Trafic et dépassement | Les interactions peuvent-elles être crédibles et réglables ? | En attente | — | Collisions, immobilisme ou comportement trop déterministe |
| E — Replay minimal | Le replay hybride est-il autonome et navigable ? | En attente | — | Taille des fichiers et compatibilité de version |
| F — Charge et accélération | La cible de voitures et l’exécution accélérée sont-elles viables ? | En attente | — | Coût combiné physique, perception, IA et enregistrement |

Conclusions autorisées : `validée`, `validée avec réserves`, `à modifier`, `non viable`.

## 3. Paramètres candidats retenus

| Domaine | Paramètre | Valeur candidate | Origine | Statut |
|---|---|---:|---|---|
| Simulation | Pas de temps physique | À mesurer | Expérience B | En attente |
| Contrôle IA | Fréquence de commande | À mesurer | Expérience C | En attente |
| Perception | Fréquence de mise à jour | À mesurer | Expérience D | En attente |
| Replay | Fréquence des images-clés | À mesurer | Expérience E | En attente |
| Replay | Fréquence de télémétrie | À mesurer | Expérience E | En attente |
| Performance | Nombre cible de voitures | 12 à 20 | Plan général | À confirmer |

## 4. Résultats par expérience

### A — Extraction Automation

- **Ticket :** #3
- **Conclusion :** en attente
- **Preuves principales :** à compléter
- **Données manquantes :** à compléter
- **Impact sur ADR-0003 :** à compléter

### B — Dynamique d’une voiture

- **Ticket :** #4
- **Conclusion :** en attente
- **Modèle testé :** à compléter
- **Écarts mesurés :** à compléter
- **Paramètres dérivés nécessaires :** à compléter

### C — Tour autonome

- **Ticket :** #5
- **Conclusion :** en attente
- **Contrôleur testé :** à compléter
- **Régularité :** à compléter
- **Différenciation des pilotes :** à compléter

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

## 5. Risques résiduels

| Risque | Probabilité | Impact | Preuve disponible | Réponse proposée |
|---|---|---|---|---|
| Données Automation insuffisantes | À évaluer | Élevé | Expérience A | Paramètres dérivés et calibration documentée |
| Modèle physique trop coûteux | À évaluer | Élevé | Expériences B et F | Simplification guidée par mesure |
| IA peu crédible en trafic | À évaluer | Élevé | Expériences C et D | Architecture en couches et scénarios statistiques |
| Replay trop volumineux | À évaluer | Moyen | Expérience E | Fréquences et compression adaptées |
| Dépendance excessive à Unity | Faible par conception | Élevé | ADR-0001 | Tests sans rendu et frontières de dépendance |

## 6. Changements requis

### Plan général

- Aucun changement identifié à ce jour.

### Architecture

- Aucun changement identifié à ce jour.

### ADR

- ADR-0001 : à confirmer après B et F.
- ADR-0002 : à confirmer après E.
- ADR-0003 : à confirmer après A.

## 7. Décision de sortie

La décision finale doit sélectionner une option :

- **Go** : les risques majeurs sont suffisamment réduits pour développer le vertical slice ;
- **Go avec réserves** : développement autorisé avec contraintes et travaux de réduction de risque intégrés ;
- **Rework** : une ou plusieurs expériences doivent être reprises avant le code de production ;
- **No-Go** : le concept ou l’architecture doit être profondément revu.

### Décision

> Non prise.

### Conditions éventuelles

> À compléter.

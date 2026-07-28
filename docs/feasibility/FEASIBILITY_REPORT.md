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
| C — Tour autonome et circuit minimal | Le contrôleur peut-il rouler sans script par virage avec un contrat de circuit minimal ? | Validée avec réserves | Moyen à bon | Contrat validé sur piste canonique, import réel et surfaces détaillées non prouvés |
| D — Trafic et dépassement | Les interactions peuvent-elles être crédibles et réglables ? | Validée avec réserves | Moyen | Interactions longues, denses ou contestées non prouvées |
| E — Replay minimal | Le replay hybride est-il autonome et navigable ? | Validée avec réserves | Moyen à bon | Format JSON non optimisé, coût à l'échelle à mesurer dans F |
| F — Charge et accélération | La cible de voitures et l’exécution accélérée sont-elles viables ? | En attente | — | Coût combiné physique, perception, IA et enregistrement |
| G — Import UR2D2 | Les fichiers UR2D2 peuvent-ils reconstruire le modèle minimal validé en C ? | En attente | — | Format opaque, échelle ambiguë ou informations insuffisantes |

Conclusions autorisées : `validée`, `validée avec réserves`, `à modifier`, `non viable`.

## 3. Paramètres candidats retenus

| Domaine | Paramètre | Valeur candidate | Origine | Statut |
|---|---|---:|---|---|
| Simulation | Pas de temps physique | `1/60 s` candidat, `1/120 s` référence de mesure | Expérience B-S05 | Candidat |
| Circuit | Schéma minimal `TrackDefinition` | v0.1 candidat | Expérience C-S01 | Candidat |
| Circuit | Tolérances de fermeture et continuité | boucle fermée implicite, polyligne validée | Expérience C-S01 | Candidat |
| Circuit | Transformation UR2D2 vers unités SI | À déterminer | Expérience G | En attente |
| Contrôle IA | Fréquence de commande | `1/60 s` candidate, `1/120 s` référence | Expérience C-S02/C-S03 | Candidat |
| Contrôle IA | Adaptation de vitesse | cible par courbure anticipée, QFC55 A9 | Expérience C-S03 | Candidat avec réserves |
| Contrôle IA | Récupération latérale | retour sous 0,75 m en moins de 7 s après perturbation | Expérience C-S04 | Candidat avec réserves |
| Contrôle IA | Profils pilote | prudent, équilibré, agressif | Expérience C-S05 | Candidat avec réserves |
| Contrôle IA | Saturation du grip | yaw demandé plafonné par limite latérale véhicule | Expérience C-S05 | Garde-fou candidat |
| Perception | Fréquence de mise à jour | À mesurer | Expérience D | En attente |
| Replay | Fréquence des images-clés | 1 s | Expérience E-S04 | Candidat avec réserves |
| Replay | Fréquence de télémétrie | 4 Hz référence, plage 1 à 20 Hz mesurée | Expérience E-S04 | Candidat avec réserves |
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
- **Conclusion :** validée avec réserves
- **Contrôleur testé :** pure pursuit à vitesse contrainte en C-S02, adaptation de vitesse par courbure avec QFC55 en C-S03, récupération d'écarts latéraux en C-S04, puis profils pilote différenciés en C-S05
- **Schéma minimal retenu :** `TrackDefinition` v0.1 candidat, indépendant de Unity et d'UR2D2
- **Invariants et tolérances :** C-S01 valide une boucle fermée implicite de 381,92 m, 24 segments, largeur minimale 10 m, courbure finie
- **Régularité :** C-S02 référence `1/120 s` : tours d'environ 30,45 s, erreur latérale moyenne 0,173 m, max 0,693 m
- **Adaptation de vitesse :** C-S03 référence `1/120 s` : trois tours en 83,33 s, vitesse moyenne 49,31 km/h, vitesse max 62,79 km/h, erreur latérale moyenne 0,231 m, max 0,807 m, aucune sortie
- **Récupération latérale :** C-S04 référence `1/120 s` : offsets `+2,75 m`, `-3,25 m` et `+3,00 m` récupérés en 1,433 s, 1,800 s et 2,467 s, aucune sortie
- **Différenciation des pilotes :** C-S05 référence `1/120 s` : prudent 115,28 s, équilibré 83,33 s, agressif 56,84 s sur trois tours, aucune sortie ; erreur latérale moyenne `0,126 m`, `0,231 m`, `0,302 m`
- **Témoin négatif C-S05 :** sur-vitesse volontaire : saturation grip `84,11 %`, ratio maximal `5,87x`, erreur latérale maximale `24,197 m`, sortie de piste attendue
- **Contrat C-S06 pour G :** `TrackDefinition` v0.1 consolidé ; champs source, invariants et valeurs dérivées listés dans `C_S06_CONTRACT_CONSOLIDATION_RESULT.md`
- **Réserve C-S03 à C-S05 :** la limite latérale utilise encore le proxy B-S04 `FrontGripG + RearGripG`, la perturbation C-S04 reste cinématique, les profils C-S05 sont heuristiques, et la saturation latérale ne distingue pas encore sous-virage et survirage
- **Données obligatoires pour un importeur :** identité, version, unités SI, axes et orientation, boucle et sens, surface principale, ligne centrale ordonnée, largeurs gauche/droite, départ, checkpoints

### D — Trafic et dépassement

- **Ticket :** #6
- **Conclusion :** validée avec réserves
- **Protocole :** `docs/feasibility/experiments/D-TRAFFIC-OVERTAKING.md`
- **Socle D-S01 :** 6 voitures projetées sur `TrackDefinition`, 6 liens de voisinage détectés, aucun hors-piste, wrap de départ validé
- **Suivi D-S02 :** 90 s derrière voiture lente, aucun contact, aucun immobilisme, gap minimal `17,50 m`, stabilisation au gap cible
- **Décision D-S03 :** 4 cas conformes / 4, dépassement candidat déclenché uniquement quand la ligne candidate est libre
- **Côte à côte D-S04 :** 45 s, aucun contact, aucun hors-piste, clearance latérale stabilisée `1,70 m`
- **Réinsertion D-S05 :** 55 s, retour dans le corridor cible en `2,98 s`, aucun contact, aucun hors-piste, gaps minimaux `32,15 m` devant et `29,24 m` derrière
- **Synthèse D-S06 :** 5 scénarios conformes / 5, 190 s dynamiques simulées, 0 contact consolidé, 0 hors-piste consolidé, 4 décisions conformes / 4
- **Réserve :** scénarios déterministes et peu nombreux ; interactions longues, denses, contestées et performance restent à couvrir

### E — Replay minimal

- **Ticket :** #7
- **Conclusion :** validée avec réserves
- **Protocole :** `docs/feasibility/experiments/E-REPLAY-MINIMAL.md`
- **Format testé :** E-S01 `AutomationLapReplay` JSON v0.1 autonome, avec piste embarquée, véhicules, frames, événements et index
- **Taille et débit :** E-S01 D-S05 replay : `148756` octets pour `55 s`, `221` frames, `3` véhicules, `3` événements
- **Navigation E-S02 :** `9` commandes, `36` samples, `2` lectures avant, `1` lecture arrière, `5` seeks, `3` clamps aux bornes, `0` échec de monotonicité
- **Événements E-S03 :** `3` événements requis trouvés / `3`, `3` jumps, `2` jumps interpolés, `3` contextes pré/post-roll valides, `0` erreur d'index
- **Échantillonnage E-S04 :** `5` profils de `1` à `20 Hz`, `56` à `1101` frames, `41831` à `719882` octets, `760.6` à `13088.8` octets/s, `0` erreur de validation
- **Compatibilité E-S05 :** `10` cas testés, `1` replay courant accepté, `9` cas incompatibles refusés, `0` mismatch ; seule la version `0.1.0` est supportée par le prototype
- **Synthèse E-S06 :** `5` scénarios validés / `5`, décision `validée avec réserves`, confiance `moyen à bon`, contrat candidat pour F et ADR-0002

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
| Replay trop volumineux | Moyenne | Moyen | Expérience E-S04 | Fréquences, compression et coût à l'échelle mesurés dans F |
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
- ADR-0002 : candidat confirmé par E, à figer après mesure de charge F.
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

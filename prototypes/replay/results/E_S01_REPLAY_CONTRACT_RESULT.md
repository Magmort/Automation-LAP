# E-S01 - Contrat replay autonome

- **Expérience :** E - Replay minimal
- **Scénario :** E-S01
- **Statut :** validé avec réserves
- **Date :** 2026-07-28T14:24:25Z
- **Objectif :** générer et charger un replay autonome sans recalculer la simulation source.
- **Réserve :** format JSON lisible, non optimisé, issu d'un scénario déterministe D-S05.

## Fichier replay

- Chemin : `prototypes/replay/results/e_s01_minimal_replay.replay.json`
- Taille : 148756 octets
- Durée : 55.00 s
- Frames : 221
- Véhicules : 3
- Événements : 3
- Points de piste embarqués : 24

## Validation

- Erreurs de structure : 0
- Checks de seek : 5
- Modes de seek : exact, interpolated
- Version supportée : oui

## Décision

E-S01 est valide avec réserves. Le prototype peut passer à E-S02 pour tester la navigation temporelle avant/arrière.

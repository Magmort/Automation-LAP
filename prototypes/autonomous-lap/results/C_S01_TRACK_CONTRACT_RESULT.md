# C-S01 - Contrat TrackDefinition

- **Experience :** C - Tour autonome et modele minimal de circuit
- **Scenario :** C-S01
- **Statut :** valide
- **Date :** 2026-07-27T17:11:29Z
- **Objectif :** valider une piste canonique dans le contrat `TrackDefinition` minimal.
- **Reserve :** C-S01 ne valide pas encore le controleur autonome.

## Synthese

- Fichier : `prototypes/autonomous-lap/fixtures/canonical_track.json`
- Erreurs de contrat : 0
- Points : 24
- Segments : 24
- Longueur : 381.92 m
- Largeur totale : 10.00 m a 10.00 m
- Courbure max absolue : 0.03578 1/m
- Echantillons preprocesses : 77

## Distances fonctionnelles

| Element | Distance curviligne |
| --- | ---: |
| Depart | 0.00 m |
| Checkpoint 1 | 0.00 m |
| Checkpoint 2 | 95.48 m |
| Checkpoint 3 | 190.96 m |
| Checkpoint 4 | 286.44 m |

## Segments

| Segment | Depuis | Vers | Longueur | Cap |
| ---: | --- | --- | ---: | ---: |
| 0 | p00 | p01 | 19.46 | 0.0772 |
| 1 | p01 | p02 | 18.65 | 0.2437 |
| 2 | p02 | p03 | 17.09 | 0.4349 |
| 3 | p03 | p04 | 15.18 | 0.6593 |
| 4 | p04 | p05 | 13.23 | 0.9681 |
| 5 | p05 | p06 | 11.87 | 1.3585 |
| 6 | p06 | p07 | 11.87 | 1.7831 |
| 7 | p07 | p08 | 13.23 | 2.1735 |
| 8 | p08 | p09 | 15.18 | 2.4823 |
| 9 | p09 | p10 | 17.09 | 2.7067 |
| 10 | p10 | p11 | 18.65 | 2.8979 |
| 11 | p11 | p12 | 19.46 | 3.0644 |
| 12 | p12 | p13 | 19.46 | -3.0644 |
| 13 | p13 | p14 | 18.65 | -2.8979 |
| 14 | p14 | p15 | 17.09 | -2.7067 |
| 15 | p15 | p16 | 15.18 | -2.4823 |
| 16 | p16 | p17 | 13.23 | -2.1735 |
| 17 | p17 | p18 | 11.87 | -1.7831 |
| 18 | p18 | p19 | 11.87 | -1.3585 |
| 19 | p19 | p20 | 13.23 | -0.9681 |
| 20 | p20 | p21 | 15.18 | -0.6593 |
| 21 | p21 | p22 | 17.09 | -0.4349 |
| 22 | p22 | p23 | 18.65 | -0.2437 |
| 23 | p23 | p00 | 19.46 | -0.0772 |

## Observations

- Le contrat minimal suffit a reconstruire une boucle fermee et orientee.
- Les distances curvilignes, tangentes, normales et courbures sont derivables sans champ source supplementaire.
- Les largeurs gauche/droite scalaires donnent une limite roulable exploitable pour les premiers controles.
- Le contrat est independant de Unity et d'UR2D2 ; G devra s'adapter vers ce format, pas l'inverse.

## Decision

C-S01 est valide. Le prototype peut passer a C-S02 pour projeter une voiture sur la piste et suivre une cible de lookahead.

# D-S01 - Perception des voisins sur piste

- **Experience :** D - Trafic et depassement
- **Scenario :** D-S01
- **Statut :** valide
- **Date :** 2026-07-27T20:21:23Z
- **Objectif :** verifier qu'une scene multi-voitures peut etre projetee sur `TrackDefinition` et produire des voisins avant/arriere coherents.
- **Reserve :** aucun changement de ligne, aucune decision de depassement et aucune collision dynamique ne sont encore simules.

## Scene

- Piste : `prototypes/autonomous-lap/fixtures/canonical_track.json`
- Scene : `prototypes/traffic/fixtures/d_s01_multicar_scene.json`
- Voitures : 6
- Longueur piste : 381.92 m
- Lookahead avant : 80.00 m
- Lookahead arriere : 55.00 m
- Corridor lateral : 2.20 m

## Resultats

| Voiture | s | Offset lat. | Vitesse | Avant | Gap avant | TTC avant | Arriere | Gap arriere |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| Red | 25.00 | 0.00 | 48.00 | blue | 37.00 | 22.20 | yellow | 46.92 |
| Blue | 62.00 | 0.20 | 42.00 | n/a | n/a | n/a | red | 37.00 |
| Green | 90.00 | -3.00 | 50.00 | n/a | n/a | n/a | n/a | n/a |
| Purple | 155.00 | 2.20 | 35.00 | orange | 15.00 | n/a | n/a | n/a |
| Orange | 170.00 | 2.40 | 50.00 | n/a | n/a | n/a | purple | 15.00 |
| Yellow | 360.00 | -0.10 | 55.00 | red | 46.92 | 24.13 | n/a | n/a |

## Metriques

- Erreurs attendues/reelles : 0
- Voitures hors piste : 0
- Erreur max de projection : 0.0000 m
- Liens voisins detectes : 6
- Plus petit gap longitudinal detecte : 15.00 m

## Decision

D-S01 est valide. Le prototype peut passer a D-S02 pour simuler un suivi longitudinal derriere une voiture plus lente.

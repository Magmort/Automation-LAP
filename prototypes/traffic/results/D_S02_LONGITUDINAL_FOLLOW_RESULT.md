# D-S02 - Suivi longitudinal derriere voiture lente

- **Experience :** D - Trafic et depassement
- **Scenario :** D-S02
- **Statut :** valide avec reserves
- **Date :** 2026-07-27T20:21:23Z
- **Objectif :** verifier qu'une voiture plus rapide peut rattraper puis suivre une voiture lente sans contact constant.
- **Reserve :** modele longitudinal simple, pas encore de decision de depassement ni de changement de ligne.

## Scene

- Piste : `prototypes/autonomous-lap/fixtures/canonical_track.json`
- Scene : `prototypes/traffic/fixtures/d_s02_longitudinal_follow_scene.json`
- Duree : 90.00 s
- Pas : 0.00833 s
- Gap cible : standstill 7.00 m + 0.90 s de headway

## Metriques

- Gap minimal : 17.50 m
- Contact ticks : 0
- Ticks immobilises : 0
- Detection voiture avant : 100.00 %
- Deceleration max suiveur : 2.57 m/s2
- Gap moyen sur les 20 dernieres secondes : 17.50 m
- Gap cible moyen sur les 20 dernieres secondes : 17.50 m
- Ecart gap moyen sur les 20 dernieres secondes : -0.00 m
- Delta vitesse moyen sur les 20 dernieres secondes : 0.00 km/h

## Decision

D-S02 est valide avec reserves. Le prototype peut passer a D-S03 pour declencher un depassement candidat.

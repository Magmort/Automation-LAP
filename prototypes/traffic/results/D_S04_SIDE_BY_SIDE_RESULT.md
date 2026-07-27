# D-S04 - Deux voitures cote a cote

- **Experience :** D - Trafic et depassement
- **Scenario :** D-S04
- **Statut :** valide avec reserves
- **Date :** 2026-07-27T20:21:23Z
- **Objectif :** verifier que deux voitures peuvent rester cote a cote avec separation laterale et limites de piste mesurables.
- **Reserve :** pas encore de manoeuvre complete de depassement ; les offsets lateraux cibles sont imposes.

## Scene

- Piste : `prototypes/autonomous-lap/fixtures/canonical_track.json`
- Scene : `prototypes/traffic/fixtures/d_s04_side_by_side_scene.json`
- Duree : 45.00 s
- Pas : 0.00833 s
- Separation laterale minimale attendue : 0.75 m

## Metriques

- Contact ticks : 0
- Hors-piste ticks : 0
- Temps cote a cote : 100.00 %
- Clearance laterale minimale : 0.50 m
- Clearance bord de piste minimale : 2.25 m
- Clearance laterale moyenne sur les 15 dernieres secondes : 1.70 m
- Delta longitudinal moyen sur les 15 dernieres secondes : 1.28 m
- Vitesse laterale max : 0.50 m/s

## Decision

D-S04 est valide avec reserves. Le prototype peut passer a D-S05 pour tester la reinsertion apres ecart.

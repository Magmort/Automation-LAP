# D-S05 - Reinsertion apres ecart

- **Experience :** D - Trafic et depassement
- **Scenario :** D-S05
- **Statut :** valide avec reserves
- **Date :** 2026-07-27T20:21:24Z
- **Objectif :** verifier qu'une voiture decalee peut revenir dans le corridor cible quand les gaps avant et arriere sont suffisants.
- **Reserve :** la decision reste deterministe et le trou est nominal ; D-S05 ne couvre pas encore les reinsertion contestees.

## Scene

- Piste : `prototypes/autonomous-lap/fixtures/canonical_track.json`
- Scene : `prototypes/traffic/fixtures/d_s05_rejoin_scene.json`
- Duree : 55.00 s
- Pas : 0.00833 s
- Offset cible : 0.00 m
- Gap securite avant : 18.00 m
- Gap securite arriere : 16.00 m

## Metriques

- Contact ticks : 0
- Hors-piste ticks : 0
- Debut reinsertion : 0.49 s
- Fin reinsertion : 3.47 s
- Duree reinsertion : 2.98 s
- Gap avant minimal pendant reinsertion : 32.15 m
- Gap arriere minimal pendant reinsertion : 29.24 m
- Temps stable dans le corridor cible apres completion : 100.00 %
- Clearance bord de piste minimale : 2.25 m
- Offset lateral final ego : 0.00 m
- Vitesse finale ego : 60.00 km/h

## Decision

D-S05 est valide avec reserves. Le prototype peut passer a D-S06 pour consolider statistiquement D.

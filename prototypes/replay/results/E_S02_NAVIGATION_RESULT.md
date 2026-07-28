# E-S02 - Navigation temporelle avant/arriere

- **Experience :** E - Replay minimal
- **Scenario :** E-S02
- **Statut :** valide avec reserves
- **Date :** 2026-07-28T14:24:39Z
- **Objectif :** parcourir un replay autonome en avant, en arriere, en pause et par seek arbitraire.
- **Reserve :** navigation hors UI Unity ; les sauts vers evenements restent dedies a E-S03.

## Entrees

- Replay : `prototypes/replay/results/e_s01_minimal_replay.replay.json`
- Script : `prototypes/replay/fixtures/e_s02_navigation_script.json`

## Metriques

- Commandes executees : 9
- Samples navigation : 36
- Lectures avant : 2
- Lectures arriere : 1
- Seek arbitraires : 5
- Pauses : 1
- Seek exacts : 22
- Seek interpoles : 14
- Clamps aux bornes : 3
- Echecs monotonicite : 0
- Replay time min/max : 0.00 s / 55.00 s

## Decision

E-S02 est valide avec reserves. Le prototype peut passer a E-S03 pour tester les evenements et le saut vers evenement.

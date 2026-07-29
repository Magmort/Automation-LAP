# E-S03 - Evenements et saut vers evenement

- **Experience :** E - Replay minimal
- **Scenario :** E-S03
- **Statut :** valide avec reserves
- **Date :** 2026-07-28T14:24:39Z
- **Objectif :** indexer les evenements du replay et sauter directement sur chaque evenement avec contexte pre/post-roll.
- **Reserve :** test hors UI ; les evenements proviennent du scenario deterministe D-S05.

## Entrees

- Replay : `prototypes/replay/results/e_s01_minimal_replay.replay.json`
- Script : `prototypes/replay/fixtures/e_s03_event_jump_script.json`

## Metriques

- Evenements replay : 3
- Evenements requis trouves : 3 / 3
- Jumps executes : 3
- Jumps interpoles : 2
- Contextes pre/post-roll valides : 3
- Clamps pre/post-roll : 2
- Erreurs index evenement : 0

## Evenements

| Evenement | Temps | Mode | Pre | Post | Offset ego |
| --- | ---:| --- | ---:| ---:| ---:|
| gap_safe_start | 0.000 | exact | 0.00 | 1.00 | 1.800 |
| rejoin_started | 0.492 | interpolated | 0.00 | 1.49 | 1.266 |
| rejoin_completed | 3.475 | interpolated | 2.73 | 4.47 | 0.150 |

## Decision

E-S03 est valide avec reserves. Le prototype peut passer a E-S04 pour mesurer taille et frequence d'echantillonnage.

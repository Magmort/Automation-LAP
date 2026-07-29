# F-S03 - Simulation acceleree sans rendu

- **Experience :** F - Charge et acceleration
- **Scenario :** F-S03
- **Statut :** valide avec reserves
- **Date :** 2026-07-28T15:09:49Z
- **Objectif :** mesurer le facteur d'acceleration atteignable sans rendu sur les profils cible.
- **Reserve :** benchmark Python hors Unity, avec etats dupliques depuis le replay E-S01.

## Seuils requis

- Facteur d'acceleration moyen : >= 20.0x
- Tick p95 moyen : <= 4.00 ms
- Ecart-type du tick moyen : <= 1.00 ms

## Profils

| Profil | Voitures | Requis | Wall moyen | Facteur | Tick moyen | Tick p95 | Veh-ticks/s | Systeme dominant | Replay bytes/s |
| --- | ---:| --- | ---:| ---:| ---:| ---:| ---:| --- | ---:|
| target_12_accel | 12 | oui | 2632.14 ms | 75.0x | 0.2413 ms | 0.4538 ms | 53981 | input (39.9 %) | 3047 |
| target_20_accel | 20 | oui | 4955.77 ms | 36.3x | 0.4556 ms | 0.7666 ms | 43598 | input (38.5 %) | 5019 |
| stress_40_accel | 40 | non | 9157.25 ms | 19.7x | 0.8447 ms | 1.4452 ms | 47224 | input (38.7 %) | 9965 |

## Decision

F-S03 est valide avec reserves. Les profils cible depassent largement le temps reel sans rendu, avec une marge suffisante pour poursuivre l'analyse du cout replay.

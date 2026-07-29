# F-S02 - Charge cible temps reel

- **Experience :** F - Charge et acceleration
- **Scenario :** F-S02
- **Statut :** valide avec reserves
- **Date :** 2026-07-28T14:55:33Z
- **Objectif :** mesurer si la boucle representative tient les profils cible 12 et 20 voitures a 60 Hz.
- **Reserve :** benchmark Python hors Unity, avec etats dupliques depuis le replay E-S01.

## Seuils

- Budget par tick : 16.667 ms
- Deadline misses requis : <= 0
- Ratio p95/budget requis : <= 0.50
- Facteur temps reel requis : >= 10.0x

## Profils

| Profil | Voitures | Requis | Wall moyen | Facteur | Tick p95 | Ratio p95/budget | Misses | Veh-ticks/s | Replay bytes/s |
| --- | ---:| --- | ---:| ---:| ---:| ---:| ---:| ---:| ---:|
| target_12 | 12 | oui | 507.13 ms | 108.6x | 0.2433 ms | 0.0146 | 0 | 78171 | 3042 |
| target_20 | 20 | oui | 749.78 ms | 73.4x | 0.3744 ms | 0.0225 | 0 | 88108 | 5021 |
| stress_40 | 40 | non | 1423.43 ms | 38.6x | 0.7124 ms | 0.0427 | 0 | 92738 | 9976 |

## Decision

F-S02 est valide avec reserves. Les profils cible 12 et 20 voitures gardent une marge temps reel confortable dans cette boucle hors rendu.

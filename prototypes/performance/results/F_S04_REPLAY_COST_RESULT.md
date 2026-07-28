# F-S04 - Cout replay detaille

- **Experience :** F - Charge et acceleration
- **Scenario :** F-S04
- **Statut :** valide avec reserves
- **Date :** 2026-07-28T17:02:45Z
- **Objectif :** isoler le cout de capture et serialization replay selon la frequence d'echantillonnage.
- **Reserve :** benchmark Python hors Unity, replay compact JSON en memoire, sans IO disque continu.

## Seuils requis

- Profil reference : 20 voitures a 4 Hz
- Part replay reference : <= 12.0 %
- Overhead mural : indicateur informatif, sensible a l'ordre d'execution Python/Windows

## Profils 20 voitures

| Hz | Wall moyen | Overhead wall | Tick moyen | Replay moyen | Part replay | Octets/s | Octets/sample | Samples |
| ---:| ---:| ---:| ---:| ---:| ---:| ---:| ---:| ---:|
| off | 709.46 ms | 0.0 % | 0.2135 ms | 0.0006 ms | 0.3 % | 0 | 0 | 0 |
| 1 | 1353.51 ms | 90.8 % | 0.4076 ms | 0.0078 ms | 1.9 % | 1254 | 1254 | 55 |
| 2 | 1516.33 ms | 113.7 % | 0.4564 ms | 0.0153 ms | 3.4 % | 2509 | 1255 | 110 |
| 4 | 1577.11 ms | 122.3 % | 0.4746 ms | 0.0284 ms | 6.0 % | 5021 | 1255 | 220 |
| 10 | 1677.69 ms | 136.5 % | 0.5053 ms | 0.0664 ms | 13.1 % | 12547 | 1255 | 550 |
| 20 | 1927.34 ms | 171.7 % | 0.5808 ms | 0.1342 ms | 23.1 % | 25104 | 1255 | 1100 |

## Stress 40 voitures

| Hz | Wall moyen | Overhead wall | Tick moyen | Replay moyen | Part replay | Octets/s | Octets/sample | Samples |
| ---:| ---:| ---:| ---:| ---:| ---:| ---:| ---:| ---:|
| off | 2736.37 ms | 0.0 % | 0.8259 ms | 0.0012 ms | 0.1 % | 0 | 0 | 0 |
| 4 | 2886.72 ms | 5.5 % | 0.8715 ms | 0.0517 ms | 5.9 % | 9976 | 2494 | 220 |
| 20 | 3538.83 ms | 29.3 % | 1.0687 ms | 0.2504 ms | 23.4 % | 49879 | 2494 | 1100 |

## Decision

F-S04 est valide avec reserves. Le cout replay de reference reste faible dans ce prototype ; la frequence augmente surtout le volume serialise.

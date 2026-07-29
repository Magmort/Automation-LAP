# F-S01 - Harnais de benchmark sans rendu

- **Experience :** F - Charge et acceleration
- **Scenario :** F-S01
- **Statut :** valide avec reserves
- **Date :** 2026-07-28T14:44:46Z
- **Objectif :** etablir un harnais reproductible pour mesurer la boucle representative hors rendu.
- **Reserve :** benchmark Python, sans Unity, avec voitures dupliquees depuis le replay E-S01.

## Environnement

- Plateforme : Windows-11-10.0.26200-SP0
- Python : 3.12.13
- CPU logiques : 32

## Metriques globales

- Profils : 4
- Repetitions par profil : 5
- Duree simulee : 55.00 s
- Voitures min/max : 1 / 40
- Erreurs : 0

## Profils

| Voitures | Wall moyen | Facteur temps reel | Vehicules-frames/s | Replay bytes/s | Pic memoire |
| ---:| ---:| ---:| ---:| ---:| ---:|
| 1 | 7.96 ms | 6916.3x | 27791 | 413 | 3368 |
| 12 | 56.95 ms | 970.7x | 46803 | 3730 | 15986 |
| 20 | 80.86 ms | 681.4x | 54763 | 6105 | 26180 |
| 40 | 180.00 ms | 307.2x | 49374 | 12077 | 55657 |

## Decision

F-S01 est valide avec reserves. Le harnais peut servir de base a F-S02 pour mesurer la charge cible temps reel.

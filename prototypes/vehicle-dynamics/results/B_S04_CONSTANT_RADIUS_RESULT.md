# B-S04 - Virage a rayon constant

- **Experience :** B - Dynamique d'une voiture
- **Scenario :** B-S04
- **Statut :** valide avec reserves
- **Date :** 2026-07-26T19:36:33Z
- **Objectif :** estimer des vitesses critiques en virage a rayon constant avec les donnees A8 disponibles.
- **Hypothese :** `FrontGripG + RearGripG` de `AccelerationToTopSpeed` est utilise comme proxy temporaire de grip lateral.
- **Reserve :** aucune courbe laterale dediee n'est encore exportee en valeurs brutes.

## Synthese

- Documents traites : 3
- Vehicules evalues : 3
- Vehicules en echec : 0
- Graphes lateraux candidats non exportes en brut : HighSpeedSteering, LowSpeedSteering

## Grip proxy

| Voiture | Points | Masse | Repartition AV | FrontGripG max | RearGripG max | Proxy max | DownForce min..max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AIXAM - Coupe GTI | 113 | 858.40 | 55.01 | 0.481 | 0.000 | 0.481 | 0.00..6.54 |
| PCM - Magmort - Carcharhini Recif | 215 | 1093.23 | 60.00 | 0.000 | 0.548 | 0.548 | -115.73..0.00 |
| QFC55 - Magmort - Carcharhini RCZ | 273 | 1278.56 | 57.60 | 0.601 | 0.640 | 1.185 | -46.87..0.00 |

## Rayons constants

| Voiture | Rayon 25 m | Rayon 50 m | Rayon 100 m |
| --- | ---: | ---: | ---: |
| AIXAM - Coupe GTI | 38.98 km/h (0.478 g) | 54.95 km/h (0.475 g) | 77.29 km/h (0.470 g) |
| PCM - Magmort - Carcharhini Recif | 41.46 km/h (0.541 g) | 58.27 km/h (0.534 g) | 80.57 km/h (0.511 g) |
| QFC55 - Magmort - Carcharhini RCZ | 61.17 km/h (1.178 g) | 86.23 km/h (1.170 g) | 121.16 km/h (1.155 g) |

## Validations

| Voiture | Valeurs finies | Graphes lateraux candidats | Graphes lateraux bruts manquants |
| --- | --- | --- | --- |
| AIXAM - Coupe GTI | oui | HighSpeedSteering, LowSpeedSteering | HighSpeedSteering, LowSpeedSteering |
| PCM - Magmort - Carcharhini Recif | oui | HighSpeedSteering, LowSpeedSteering | HighSpeedSteering, LowSpeedSteering |
| QFC55 - Magmort - Carcharhini RCZ | oui | HighSpeedSteering, LowSpeedSteering | HighSpeedSteering, LowSpeedSteering |

## Observations

- Les trois voitures produisent des vitesses critiques finies pour les trois rayons testes.
- Le classement obtenu est plausible pour un test proxy : QFC55 > PCM > AIXAM.
- Les valeurs de vitesse sont exprimees en km/h par inference, car elles correspondent aux vitesses de performance deja confirmees.
- Le resultat ne valide pas encore un modele lateral physique : il valide seulement que B peut executer un scenario de virage reproductible avec les donnees actuelles.
- Les graphes `LowSpeedSteering` et `HighSpeedSteering` sont visibles dans l'inventaire, mais pas encore exportes en series brutes A8.

## Decision

B-S04 est valide avec reserves. Pour un modele de virage plus fiable, une extension future de A devrait exporter les graphes lateraux ou une donnee d'adherence laterale explicite.

# B-S06 - Sensibilite inter-voitures

- **Experience :** B - Dynamique d'une voiture
- **Scenario :** B-S06
- **Statut :** valide avec reserves
- **Date :** 2026-07-27T14:37:08Z
- **Objectif :** verifier que les resultats B-S02 a B-S05 conservent des differences plausibles entre les trois voitures.
- **Reserve :** les metriques de direction restent issues d'une normalisation de graphes Automation dont l'unite est inconnue.

## Sources

- B-S02 : `prototypes/vehicle-dynamics/results/b_s02_acceleration_curve_summary.json`
- B-S03 : `prototypes/vehicle-dynamics/results/b_s03_braking_curve_summary.json`
- B-S04 : `prototypes/vehicle-dynamics/results/b_s04_steering_graphs_summary.json`
- B-S05 : `prototypes/vehicle-dynamics/results/b_s05_transitions_summary.json`

## Metriques consolidees

| Voiture | Vmax | 0-100 | 100->fin | High steering max | Distance transition | Vitesse finale transition | Lateral G modele |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AIXAM - Coupe GTI | 115.18 | 50.07 | 3.42 | 15.93 | 17.49 | 7.70 | 0.006 |
| PCM - Magmort - Carcharhini Recif | 223.01 | 5.69 | 2.94 | 11.73 | 202.00 | 107.36 | 2.584 |
| QFC55 - Magmort - Carcharhini RCZ | 287.79 | 5.40 | 2.63 | 15.83 | 221.29 | 107.28 | 1.874 |

## Classements

| Metrique | Classement | Ecart relatif |
| --- | --- | ---: |
| Vmax | QFC55 - Magmort - Carcharhini RCZ (287.79) > PCM - Magmort - Carcharhini Recif (223.01) > AIXAM - Coupe GTI (115.18) | 60.0 % |
| 0-100 | QFC55 - Magmort - Carcharhini RCZ (5.40) > PCM - Magmort - Carcharhini Recif (5.69) > AIXAM - Coupe GTI (50.07) | 89.2 % |
| 100->fin | QFC55 - Magmort - Carcharhini RCZ (2.63) > PCM - Magmort - Carcharhini Recif (2.94) > AIXAM - Coupe GTI (3.42) | 23.0 % |
| High steering max | AIXAM - Coupe GTI (15.93) > QFC55 - Magmort - Carcharhini RCZ (15.83) > PCM - Magmort - Carcharhini Recif (11.73) | 26.4 % |
| Distance transition | QFC55 - Magmort - Carcharhini RCZ (221.29) > PCM - Magmort - Carcharhini Recif (202.00) > AIXAM - Coupe GTI (17.49) | 92.1 % |
| Vitesse finale transition | PCM - Magmort - Carcharhini Recif (107.36) > QFC55 - Magmort - Carcharhini RCZ (107.28) > AIXAM - Coupe GTI (7.70) | 92.8 % |
| Lateral G modele | PCM - Magmort - Carcharhini Recif (2.58) > QFC55 - Magmort - Carcharhini RCZ (1.87) > AIXAM - Coupe GTI (0.01) | 99.8 % |

## Controles attendus

| Controle | Resultat |
| --- | --- |
| AIXAM reste la plus lente en Vmax | oui |
| QFC55 reste la plus rapide en Vmax | oui |
| QFC55 reste la plus rapide sur 0-100 | oui |
| QFC55 reste la plus rapide sur 100->fin | oui |
| AIXAM reste la moins couvrante sur la transition | oui |

## Observations

- Les trois voitures restent nettement differenciees sur les metriques longitudinales.
- La QFC55 domine en Vmax, 0-100 et freinage 100->fin, ce qui correspond aux resultats relus depuis Automation.
- Le scenario de transition separe clairement l'AIXAM des deux voitures rapides.
- Les metriques de direction differencient les voitures, mais leur interpretation physique reste reservee tant que les unites ne sont pas confirmees.
- `1/60 s` peut etre retenu comme pas candidat pour C, avec `1/120 s` comme reference de verification pendant les prochains prototypes.

## Decision

B-S06 est valide avec reserves. L'experience B peut etre conclue comme viable pour alimenter C, a condition de conserver la direction comme modele calibrable et de ne pas presenter les graphes Steering comme une adherence laterale brute.

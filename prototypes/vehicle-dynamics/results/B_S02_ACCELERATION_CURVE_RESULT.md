# B-S02 - Relecture acceleration 0 a Vmax

- **Experience :** B - Dynamique d'une voiture
- **Scenario :** B-S02
- **Statut :** valide
- **Date :** 2026-07-26T19:26:10Z
- **Objectif :** construire des interpolateures sur `AccelerationToTopSpeed` sans recalculer la courbe Automation.
- **Unites :** vitesse et distance conservees en unites natives Automation ; le temps est relu comme secondes.

## Synthese

- Documents traites : 3
- Courbes valides : 3
- Courbes en echec : 0
- Erreur max d'interpolation sur l'axe temps aux points source : 0.000000000000

## Reperes par voiture

| Voiture | Points | Vmax | Temps Vmax | Distance Vmax | 0-50 | 0-100 | Puissance max | Rapport max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AIXAM - Coupe GTI | 113 | 115.18 | 75.25 | 1559.54 | 20.19 | 50.07 | 15.02 | 1 |
| PCM - Magmort - Carcharhini Recif | 215 | 223.01 | 49.40 | 2380.77 | 2.66 | 5.69 | 148.93 | 3 |
| QFC55 - Magmort - Carcharhini RCZ | 273 | 287.79 | 73.70 | 4644.82 | 2.28 | 5.40 | 183.25 | 6 |

## Validations de courbe

| Voiture | Vitesse monotone | Temps monotone | Distance monotone | Valeurs finies | Erreur vitesse | Erreur distance |
| --- | --- | --- | --- | --- | ---: | ---: |
| AIXAM - Coupe GTI | oui | oui | oui | oui | 0.000000000000 | 0.000000000000 |
| PCM - Magmort - Carcharhini Recif | non | oui | oui | oui | 0.000000000000 | 0.000000000000 |
| QFC55 - Magmort - Carcharhini RCZ | non | oui | oui | oui | 0.000000000000 | 0.000000000000 |

## Variations de vitesse

| Voiture | Baisse de vitesse detectee | Nombre | Baisse max | Baisse cumulee |
| --- | --- | ---: | ---: | ---: |
| AIXAM - Coupe GTI | non | 0 | 0.000000 | 0.000000 |
| PCM - Magmort - Carcharhini Recif | oui | 1 | 1.043923 | 1.043923 |
| QFC55 - Magmort - Carcharhini RCZ | oui | 1 | 1.115045 | 1.115045 |

## Classement observe

1. QFC55 - Magmort - Carcharhini RCZ - Vmax 287.79, temps Vmax 73.70
2. PCM - Magmort - Carcharhini Recif - Vmax 223.01, temps Vmax 49.40
3. AIXAM - Coupe GTI - Vmax 115.18, temps Vmax 75.25

## Observations

- Les trois courbes `AccelerationToTopSpeed` sont chargeables et interpolables.
- Les reperes 0-50, 0-100 et Vmax utilisent le premier passage a la vitesse cible.
- Les petites baisses de vitesse en fin de courbe sont conservees comme information source, sans les lisser.
- Les valeurs restent etiquetees en unites natives Automation tant que les unites des graphes ne sont pas confirmees.
- B-S02 ne simule pas encore l'acceleration : il rend la courbe Automation exploitable par les prochains jalons.

## Decision

B-S02 est valide. Le prototype peut passer a B-S03 pour appliquer la meme logique aux courbes de freinage.

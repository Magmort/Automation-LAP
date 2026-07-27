# B-S03 - Relecture freinage

- **Experience :** B - Dynamique d'une voiture
- **Scenario :** B-S03
- **Statut :** valide
- **Date :** 2026-07-26T19:30:32Z
- **Objectif :** construire des interpolateures sur `Braking` et comparer l'axe de `BrakingVGrip`.
- **Unites :** vitesse, force, grip et aire vitesse-temps conservees en unites natives Automation.

## Synthese

- Documents traites : 3
- Courbes valides : 3
- Courbes en echec : 0
- Ecart max entre axes `Braking.Speed` et `BrakingVGrip.Speed` : 0.000000000000
- Erreur max d'interpolation sur l'axe temps aux points source : 0.000000000000

## Reperes par voiture

| Voiture | Points | Vitesse depart | Vitesse fin | Duree courbe | Aire vitesse-temps | 200->fin | 100->fin | 50->fin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AIXAM - Coupe GTI | 98 | 113.68 | 0.41 | 3.88 | 219.70 | n/a | 3.42 | 1.72 |
| PCM - Magmort - Carcharhini Recif | 159 | 220.56 | 1.21 | 6.32 | 686.78 | 5.77 | 2.94 | 1.46 |
| QFC55 - Magmort - Carcharhini RCZ | 184 | 284.95 | 0.03 | 7.32 | 1027.69 | 5.21 | 2.63 | 1.32 |

## Validations de courbe

| Voiture | Vitesse descendante | Temps montant | Valeurs finies | Axe BrakingVGrip identique | Erreur vitesse |
| --- | --- | --- | --- | --- | ---: |
| AIXAM - Coupe GTI | oui | oui | oui | oui | 0.000000000000 |
| PCM - Magmort - Carcharhini Recif | oui | oui | oui | oui | 0.000000000000 |
| QFC55 - Magmort - Carcharhini RCZ | oui | oui | oui | oui | 0.000000000000 |

## BrakingVGrip

| Voiture | Force AV | Grip AV | Marge AV min | Force AR | Grip AR | Marge AR min | Essieu limitant |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| AIXAM - Coupe GTI | 2939.05 | 2836.20..2860.53 | -102.85 | 950.06 | 856.94..858.25 | -93.12 | front |
| PCM - Magmort - Carcharhini Recif | 4030.90 | 4037.00..4332.71 | 6.11 | 1345.35 | 1048.65..1245.39 | -296.70 | rear |
| QFC55 - Magmort - Carcharhini RCZ | 5946.79 | 5177.28..5356.30 | -769.52 | 1917.06 | 1613.19..1661.62 | -303.87 | front |

## Observations

- Les trois courbes `Braking` sont chargeables et interpolables sur l'axe temps.
- L'axe `BrakingVGrip.Speed` correspond a `Braking.Speed` pour les trois voitures.
- Les durees 200->fin, 100->fin et 50->fin utilisent le premier passage descendant sous la vitesse cible.
- L'aire vitesse-temps est conservee en unite native Automation ; elle peut servir de distance candidate seulement apres confirmation d'unite.
- Les forces et grips avant/arriere de `BrakingVGrip` sont exploitables comme series, mais leur unite reste inconnue.

## Decision

B-S03 est valide. Les courbes longitudinales d'acceleration et de freinage sont maintenant relisibles sans recalculer Automation.

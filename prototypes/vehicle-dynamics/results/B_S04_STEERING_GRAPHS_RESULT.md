# B-S04 - Analyse des graphes de direction A9

- **Experience :** B - Dynamique d'une voiture
- **Scenario :** complement B-S04
- **Statut :** valide avec reserves
- **Date :** 2026-07-26T20:04:07Z
- **Objectif :** evaluer l'utilite de `LowSpeedSteering` et `HighSpeedSteering` pour remplacer ou completer le proxy de virage.
- **Reserve :** ces graphes ne donnent pas directement un rayon de virage ni une adherence laterale brute.

## Synthese

- Documents traites : 3
- Vehicules valides : 3
- Vehicules en echec : 0

## Domaine des graphes

| Voiture | Low points | Low speed max | High points | High speed max | Troncature |
| --- | ---: | ---: | ---: | ---: | ---: |
| AIXAM - Coupe GTI | 3764 | 70.29 | 1525 | 158.10 | 0 |
| PCM - Magmort - Carcharhini Recif | 4259 | 74.71 | 1657 | 164.73 | 0 |
| QFC55 - Magmort - Carcharhini RCZ | 5438 | 84.32 | 2157 | 187.71 | 0 |

## Pics Steering

| Voiture | Low pic | Low vitesse pic | Low fin | High pic | High vitesse pic | High fin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AIXAM - Coupe GTI | 9.18 | 69.28 | 0.22 | 15.93 | 138.32 | 0.22 |
| PCM - Magmort - Carcharhini Recif | 7.48 | 73.48 | 0.20 | 11.73 | 139.49 | 0.21 |
| QFC55 - Magmort - Carcharhini RCZ | 8.60 | 82.71 | 0.29 | 15.83 | 160.14 | 0.29 |

## Enveloppe Under/Over

| Voiture | Low inside | Low croisements | High inside | High croisements |
| --- | ---: | --- | ---: | --- |
| AIXAM - Coupe GTI | 97.8 % | over: 0.00 ; under: 0.00, 69.52 | 59.4 % | over: 0.00 ; under: 0.00, 122.38 |
| PCM - Magmort - Carcharhini Recif | 29.9 % | over: 0.00, 59.88 ; under: 0.00, 72.34 | 30.7 % | over: 0.00 ; under: 0.00, 92.43 |
| QFC55 - Magmort - Carcharhini RCZ | 27.3 % | over: 0.00, 70.86 ; under: 0.00, 83.31 | 25.4 % | over: 0.00, 20.22, 127.57 ; under: 0.00, 158.22 |

## Observations

- Les graphes A9 sont complets et exploitables numeriquement pour les trois voitures.
- `Speed` est un axe monotone sur les six graphes analyses.
- `Steering` monte jusqu'a un pic puis chute en fin de domaine ; ce comportement doit etre conserve, pas lisse.
- `UnderSteer` et `OverSteer` fournissent une enveloppe utile pour qualifier le comportement de direction.
- Ces graphes sont plus utiles que le proxy B-S04 pour l'analyse de direction, mais ne remplacent pas seuls une formule de vitesse critique en rayon constant.

## Decision

Les graphes de direction A9 sont utiles pour completer B-S04. Ils doivent etre conserves dans le pipeline, avec interpretation prudente et unites `unknown` tant que la signification exacte n'est pas confirmee.

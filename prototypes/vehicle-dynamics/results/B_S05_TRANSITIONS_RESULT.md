# B-S05 - Transitions throttle / frein / direction

- **Experience :** B - Dynamique d'une voiture
- **Scenario :** B-S05
- **Statut :** valide avec reserves
- **Date :** 2026-07-26T20:14:33Z
- **Objectif :** verifier qu'un etat 2D minimal reste stable quand acceleration, freinage et direction sont melanges.
- **Entrees :** exports A9 dans `outputs/a9-raw-vehicle-data/`.
- **Reserve :** le modele de cap utilise une hypothese de braquage normalise ; ce n'est pas encore un modele lateral physique.

## Scenario de controle

| Temps | Throttle | Frein | Direction |
| --- | ---: | ---: | ---: |
| 0.0-3.0 s | 1.00 | 0.00 | 0.00 |
| 3.0-5.0 s | 0.85 | 0.00 | +0.35 |
| 5.0-6.5 s | 0.00 | 0.45 | +0.50 |
| 6.5-9.0 s | 0.85 | 0.00 | -0.45 |
| 9.0-12.0 s | 0.30 | 0.00 | 0.00 |

## Synthese

- Documents traites : 3
- Vehicules valides : 3
- Vehicules en echec : 0
- Pas testes : 0.03333 s, 0.01667 s, 0.00833 s
- Reference stabilite : 0.00833 s

## Etats finaux au pas 1/120 s

| Voiture | Vitesse finale | Distance X | Distance Y | Cap final | Vitesse max | Lateral G modele max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AIXAM - Coupe GTI | 7.70 | 17.49 | 0.24 | 0.0211 | 11.95 | 0.006 |
| PCM - Magmort - Carcharhini Recif | 107.36 | 179.45 | 92.75 | 0.0885 | 107.36 | 2.584 |
| QFC55 - Magmort - Carcharhini RCZ | 107.28 | 194.50 | 105.53 | 0.2511 | 107.28 | 1.874 |

## Stabilite par pas de temps

| Voiture | dt | Ecart position | Limite position | Ecart cap | Ecart vitesse | Limite vitesse | Valeurs finies | Stable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| AIXAM - Coupe GTI | 0.03333 | 0.0021 | 0.7500 | 0.000025 | 0.0000 | 0.3500 | oui | oui |
| AIXAM - Coupe GTI | 0.01667 | 0.0005 | 0.7500 | 0.000006 | 0.0000 | 0.3500 | oui | oui |
| AIXAM - Coupe GTI | 0.00833 | 0.0000 | 0.7500 | 0.000000 | 0.0000 | 0.3500 | oui | oui |
| PCM - Magmort - Carcharhini Recif | 0.03333 | 0.2520 | 4.0400 | 0.000686 | 0.0396 | 1.6104 | oui | oui |
| PCM - Magmort - Carcharhini Recif | 0.01667 | 0.9881 | 4.0400 | 0.007764 | 0.0067 | 1.6104 | oui | oui |
| PCM - Magmort - Carcharhini Recif | 0.00833 | 0.0000 | 4.0400 | 0.000000 | 0.0000 | 1.6104 | oui | oui |
| QFC55 - Magmort - Carcharhini RCZ | 0.03333 | 1.4563 | 4.4257 | 0.003769 | 1.1286 | 1.6092 | oui | oui |
| QFC55 - Magmort - Carcharhini RCZ | 0.01667 | 3.5501 | 4.4257 | 0.023256 | 0.3726 | 1.6092 | oui | oui |
| QFC55 - Magmort - Carcharhini RCZ | 0.00833 | 0.0000 | 4.4257 | 0.000000 | 0.0000 | 1.6092 | oui | oui |

## Usage des graphes de direction

| Voiture | dt | LowSpeedSteering | HighSpeedSteering |
| --- | ---: | ---: | ---: |
| AIXAM - Coupe GTI | 0.03333 | 360 | 0 |
| AIXAM - Coupe GTI | 0.01667 | 720 | 0 |
| AIXAM - Coupe GTI | 0.00833 | 1440 | 0 |
| PCM - Magmort - Carcharhini Recif | 0.03333 | 172 | 188 |
| PCM - Magmort - Carcharhini Recif | 0.01667 | 344 | 376 |
| PCM - Magmort - Carcharhini Recif | 0.00833 | 687 | 753 |
| QFC55 - Magmort - Carcharhini RCZ | 0.03333 | 219 | 141 |
| QFC55 - Magmort - Carcharhini RCZ | 0.01667 | 455 | 265 |
| QFC55 - Magmort - Carcharhini RCZ | 0.00833 | 902 | 538 |

## Observations

- Les trois voitures restent finies aux trois pas de temps testes.
- Les ecarts `1/30 s` et `1/60 s` restent bornes face a la reference `1/120 s`.
- L'acceleration vient de la pente de `AccelerationToTopSpeed.Speed/Time`, le freinage de la pente de `Braking.Speed/Time`.
- La direction utilise `LowSpeedSteering` puis `HighSpeedSteering` comme reponse normalisee selon la vitesse.
- Les positions sont en metres sous hypothese `Speed` en km/h et `Time` en secondes, coherente avec les champs de performance exportes.

## Decision

B-S05 est valide avec reserves. Le prototype peut integrer acceleration, freinage et direction dans un etat 2D minimal, mais le modele lateral doit rester marque comme hypothese tant que les unites exactes des graphes de direction ne sont pas confirmees.

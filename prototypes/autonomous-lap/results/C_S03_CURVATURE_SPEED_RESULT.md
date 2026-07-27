# C-S03 - Adaptation de vitesse par courbure

- **Experience :** C - Tour autonome et modele minimal de circuit
- **Scenario :** C-S03
- **Statut :** valide avec reserves
- **Date :** 2026-07-27T17:11:30Z
- **Objectif :** utiliser la QFC55 pour adapter la vitesse selon la courbure de la piste canonique.
- **Reserve :** la limite laterale reste derivee du proxy B-S04 `FrontGripG + RearGripG` avec facteur de securite.

## Donnees vehicule

- Vehicule : QFC55 - Magmort - Carcharhini RCZ
- Exporteur : `0.1.13-a9-steering-raw-graphs`
- Source : `outputs/a9-raw-vehicle-data/QFC55 - Magmort Carcharhini RCZ/automation-lap-raw-vehicle-data.json`
- Vmax courbe : 287.79 km/h
- Grip proxy max : 1.185 g
- Limite laterale utilisee : 1.008 g
- Acceleration : pente `AccelerationToTopSpeed.Speed/Time`
- Freinage : pente `Braking.Speed/Time`

## Resultats par pas de temps

| dt | Tours | Duree | Vitesse moy. | Vitesse max | Cible min | Erreur lat. moy. | Erreur lat. max | Lat. G max | Sorties | Variation tours | Stable |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0.01667 | 3 | 83.35 | 49.32 | 62.82 | 34.88 | 0.230 | 0.800 | 0.446 | 0 | 1.92 % | oui |
| 0.00833 | 3 | 83.33 | 49.31 | 62.79 | 34.87 | 0.231 | 0.807 | 0.446 | 0 | 1.95 % | oui |

## Temps au tour

| dt | Tour 1 | Tour 2 | Tour 3 | Throttle | Frein |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.01667 | 28.13 | 27.60 | 27.60 | 47.1 % | 50.2 % |
| 0.00833 | 28.13 | 27.60 | 27.59 | 47.3 % | 50.6 % |

## Reference 1/120 s

- Duree totale : 83.33 s
- Vitesse moyenne : 49.31 km/h
- Vitesse max : 62.79 km/h
- Erreur laterale moyenne : 0.231 m
- Erreur laterale max : 0.807 m
- Lateral G modele max : 0.446 g

## Observations

- La QFC55 utilise ses propres courbes d'acceleration et de freinage A9 pour rejoindre la vitesse cible.
- La vitesse cible varie avec la courbure anticipee de la piste, sans script par virage.
- Les deux pas de temps terminent trois tours sans sortie de piste.
- La limite laterale reste un proxy issu de B-S04 ; elle doit etre recalibree quand le modele lateral sera mieux defini.

## Decision

C-S03 est valide avec reserves. Le prototype peut passer a C-S04 pour tester la recuperation apres perturbation laterale avec le meme vehicule et la meme logique de vitesse.

# C-S04 - Recuperation apres perturbation laterale

- **Experience :** C - Tour autonome et modele minimal de circuit
- **Scenario :** C-S04
- **Statut :** valide avec reserves
- **Date :** 2026-07-27T17:11:30Z
- **Objectif :** verifier que le controleur C-S03 recupere des ecarts lateraux imposes sans logique speciale par virage.
- **Reserve :** la limite laterale reste derivee du proxy B-S04 `FrontGripG + RearGripG` avec facteur de securite.

## Donnees vehicule

- Vehicule : QFC55 - Magmort - Carcharhini RCZ
- Exporteur : `0.1.13-a9-steering-raw-graphs`
- Source : `outputs/a9-raw-vehicle-data/QFC55 - Magmort Carcharhini RCZ/automation-lap-raw-vehicle-data.json`
- Limite laterale utilisee : 1.008 g

## Perturbations

- Seuil de recuperation : 0.75 m d'erreur laterale absolue
- Temps maximum autorise : 7.00 s
- Application : deplacement lateral instantane de la voiture, vitesse et cap conserves.

## Resultats par pas de temps

| dt | Tours | Duree | Erreur lat. moy. | Erreur lat. max | Recuperation max | Sorties | Variation tours | Lat. G max | Stable |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0.01667 | 3 | 83.35 | 0.347 | 3.250 | 2.450 | 0 | 1.92 % | 0.669 | oui |
| 0.00833 | 3 | 83.33 | 0.348 | 3.250 | 2.467 | 0 | 1.95 % | 0.668 | oui |

## Recuperations reference 1/120 s

| Perturbation | Offset | Temps | Progression | Recuperation | Max erreur pendant recup. |
| --- | ---: | ---: | ---: | ---: | ---: |
| p1-left-entry | 2.75 m | 15.45 s | 210.05 m | 1.433 s | 2.750 m |
| p2-right-mid | -3.25 m | 38.35 s | 515.59 m | 1.800 s | 3.250 m |
| p3-left-late | 3.00 m | 59.48 s | 821.12 m | 2.467 s | 3.000 m |

## Reference 1/120 s

- Duree totale : 83.33 s
- Vitesse moyenne : 49.32 km/h
- Vitesse max : 62.80 km/h
- Erreur laterale moyenne : 0.348 m
- Erreur laterale max : 3.250 m
- Recuperation la plus lente : 2.467 s

## Observations

- Les perturbations sont appliquees a des progressions fixes et non a des virages scripts.
- Le controleur conserve la logique C-S03 : vitesse cible par courbure, pure pursuit et courbes QFC55.
- Les deux pas de temps terminent trois tours sans sortie de piste et recuperent les trois ecarts lateraux.

## Decision

C-S04 est valide avec reserves. Le prototype peut passer a C-S05 pour differencier des profils de competence pilote.

# C-S02 - Suivi de trajectoire a vitesse contrainte

- **Experience :** C - Tour autonome et modele minimal de circuit
- **Scenario :** C-S02
- **Statut :** valide
- **Date :** 2026-07-27T17:11:29Z
- **Objectif :** verifier qu'une voiture peut suivre la ligne centrale par projection et cible lookahead, sans script par virage.
- **Reserve :** la vitesse est volontairement contrainte ; l'adaptation par courbure est repoussee a C-S03.

## Synthese

- Fichier piste : `prototypes/autonomous-lap/fixtures/canonical_track.json`
- Longueur piste : 381.92 m
- Vitesse cible : 45.00 km/h
- Lookahead : 14.00 m
- Tours cibles : 3

## Resultats par pas de temps

| dt | Tours | Duree | Moyenne erreur lat. | RMS erreur lat. | Max erreur lat. | Sorties | Variation tours | Stable |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0.01667 | 3 | 91.37 | 0.172 | 0.220 | 0.689 | 0 | 0.00 % | oui |
| 0.00833 | 3 | 91.35 | 0.173 | 0.222 | 0.693 | 0 | 0.03 % | oui |

## Temps au tour

| dt | Tour 1 | Tour 2 | Tour 3 |
| ---: | ---: | ---: | ---: |
| 0.01667 | 30.45 | 30.45 | 30.45 |
| 0.00833 | 30.45 | 30.45 | 30.44 |

## Reference 1/120 s

- Erreur laterale moyenne : 0.173 m
- Erreur laterale max : 0.693 m
- Braquage max utilise : 0.0931 rad
- Erreur de cap max vers cible : 0.2594 rad

## Observations

- Le controleur utilise uniquement la projection sur `TrackDefinition`, une cible lookahead et une loi pure pursuit.
- Aucun virage n'est scripté : la meme logique parcourt toute la boucle.
- Les deux pas de temps testés terminent trois tours sans sortie de piste.
- La vitesse est maintenue constante pour isoler le probleme de suivi ; C-S03 ajoutera l'adaptation par courbure.

## Decision

C-S02 est valide. Le prototype peut passer a C-S03 pour moduler la vitesse selon la courbure et tester un comportement plus proche d'un tour autonome utilisable.

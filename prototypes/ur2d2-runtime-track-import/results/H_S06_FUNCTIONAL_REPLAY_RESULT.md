# H-S06 - Validation fonctionnelle sur fond runtime

- **Experience :** H - Import depuis les vrais fichiers de tracks UR2D2
- **Scenario :** H-S06
- **Statut :** functional-replay-ready-for-validation
- **Date :** 2026-07-29T20:50:17Z
- **Package :** `prototypes/ur2d2-runtime-track-import/results/h_s05_import_package.json`
- **Vehicule :** QFC55 - Magmort - Carcharhini RCZ

## Decision du jalon

H-S06 confirme que le paquet H-S05 peut alimenter le controleur autonome C-S03 et produire un replay coherent sur le fond runtime UR2D2.

## Controles

| Controle | Resultat |
| --- | --- |
| `packageKindValid` | oui |
| `packageReadyH05` | oui |
| `trackDefinitionValid` | oui |
| `vehicleDataValid` | oui |
| `allTimeStepsStable` | oui |
| `referenceRunStable` | oui |
| `referenceRunCompletedThreeLaps` | oui |
| `referenceRunNoOffTrack` | oui |
| `runtimeBackgroundAvailable` | oui |
| `replaySamplesPresent` | oui |
| `extrasAvailable` | oui |

## Reference 1/120 s

- Tours : 3
- Duree totale : 62.66 s
- Temps au tour : 20.89 s, 20.88 s, 20.87 s
- Vitesse moyenne : 46.09 km/h
- Vitesse max : 80.72 km/h
- Erreur laterale moyenne : 0.927 m
- Erreur laterale max : 3.042 m
- Sorties de piste : 0

## Resultats par pas de temps

| dt | Tours | Duree | Vitesse moy. | Erreur lat. moy. | Erreur lat. max | Sorties | Stable |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0.01667 | 3 | 62.67 | 46.10 | 0.923 | 3.030 | 0 | oui |
| 0.00833 | 3 | 62.66 | 46.09 | 0.927 | 3.042 | 0 | oui |

## Reserves

- Le replay utilise le modele C-S03 actuel ; il valide le chemin d'import, pas encore le modele physique final.
- Les murs et la pitlane sont disponibles et rendus, mais ne sont pas encore des contraintes de conduite.
- Le rendu s'appuie sur les PNG locaux UR2D2 par reference de chemin, sans redistribution des assets.

## Prochaine etape

Apres validation visuelle, H peut etre cloturee ou prolongee avec des scenarios tenant compte des murs et de la pitlane.

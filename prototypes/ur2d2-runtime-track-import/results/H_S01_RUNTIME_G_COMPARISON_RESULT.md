# H-S01 - Comparaison runtime avec G

- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2
- **Scénario :** H-S01
- **Statut :** ready-for-h-s02-runtime-reader
- **Date :** 2026-07-29T17:26:16Z
- **Fixture runtime :** `R00_runtime_track_2`
- **Référence G :** `T05_start_and_checkpoints`

## Décision du jalon

H-S01 valide que le package runtime contient assez d'indices structurés pour lancer un lecteur brut H-S02.

## Fichiers runtime

| Fichier | Taille | Signature | SHA-256 court |
| --- | ---: | --- | --- |
| `track.data` | 35124 | unknown-binary | `566aa74f2894` |
| `track_info.data` | 345 | unknown-binary | `d4c3941e1e05` |
| `track_editor.sav` | 3655 | unknown-binary | `4483667becae` |

## Contrôles

| Contrôle | Résultat |
| --- | --- |
| `runtimePackagePresent` | oui |
| `trackInfoPresent` | oui |
| `editorSavPresent` | oui |
| `runtimeContainsAllPrimaryRoadKeyCoordinates` | oui |
| `runtimeContainsExactPrimaryRoadKeyPairs` | oui |
| `compactRuntimeCheckpointsDetected` | oui |
| `compactRuntimeCheckpointsMatchEditor` | oui |

## Relation avec G

- Match exact du `track_editor.sav` avec une fixture G : aucune.
- Les coordonnées de clés route G sont présentes dans `track.data`.
- Les checkpoints runtime compacts correspondent aux coordonnées de checkpoints G.

### Clés route

| Key | x | y | occurrences x | occurrences y | paire exacte |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1424.000 | 1072.000 | 11 | 206 | 2 |
| 1 | 2480.000 | 1072.000 | 7 | 206 | 0 |
| 2 | 2480.000 | 1712.000 | 7 | 408 | 2 |
| 3 | 1424.000 | 1712.000 | 11 | 408 | 0 |

### Checkpoints

| Runtime offset | x | y | rotation runtime | Match G | écart | delta rotation |
| ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 12 | 1356.068 | 1629.606 | 287.835 | Checkpoint 2 | 0.000000 | 0.000000 |
| 43 | 2368.645 | 1712.000 | 360.000 | Checkpoint 1 | 0.000000 | 0.000000 |
| 74 | 2239.639 | 1072.000 | 180.000 | Finish | 0.000000 | 0.000000 |

## Métadonnées lues

- `track_info.data` : `C@First_Track` ; `track:2/2796.14` ; `flag_andorra` ; `?ffffff` ; `?Road Course` ; `?medium` ; `soft` ; `clear` ; `?[D.C.o.K] Magmort`
- `track.data` : `@checkpoint` ; `?checkpoint` ; `checkpoint` ; `DY  ER` ; `Ds> E` ; `g E=E` ; ` E!q` ; ` E9@` ; `!E B` ; ` EF{` ; ` Edc` ; `D:s E,{`

## Notes

- `track.data` contient les coordonnées brutes des clés de route G et des points runtime échantillonnés.
- Les premiers records `checkpoint` de `track.data` correspondent aux checkpoints G avec une rotation runtime égale à rotation éditeur - 90 degrés.
- `track_info.data` porte les métadonnées visibles de piste, notamment le nom, l'identifiant `track:2/2796.14`, le pays, le type et les conditions.
- `track_editor.sav` est présent dans le package runtime, mais son hash ne correspond pas aux fixtures G déjà inventoriées parce que la piste a été réexportée après les corrections visuelles.

## Prochaine étape

H-S02 peut produire un `UR2D2RuntimeTrackData` brut en lisant prioritairement `track.data` et `track_info.data`, avec `track_editor.sav` comme référence de comparaison et non comme source obligatoire.

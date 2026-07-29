# H-S01b - Inventaire exhaustif des éléments runtime

- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2
- **Scénario :** H-S01b
- **Statut :** complete-runtime-element-map
- **Date :** 2026-07-29T19:30:14Z
- **Fixture runtime :** `R00_runtime_track_2`

## Décision du jalon

Tous les éléments attendus sont localisés dans le package runtime : soit comme source vectorielle dans `track_editor.sav`, soit comme signal exploitable dans `track.data`, soit comme rendu/calque raster runtime.

## Contrôles

| Contrôle | Résultat |
| --- | --- |
| `allExpectedElementsFoundInEditorSav` | oui |
| `allExpectedElementsLocalizedInRuntimePackage` | oui |
| `compactCheckpointRecordsMatchEditorSav` | oui |
| `gravelLayerHasLocalizedAlphaBBox` | oui |

## Inventaire attendu

| Élément | Attendu | Lu dans track_editor.sav | Localisation runtime | Confiance | Preuve courte | Offsets / couche |
| --- | ---: | ---: | --- | --- | --- | --- |
| Segments de route | 4 | 4 | `localized-sampled-track-data` | high | La route est lue comme trace vectorielle dans track_editor.sav et présente comme blocs échantillonnés dans track.data. | runtime `0x061d`, `0x0621`, `0x10a5`, `0x10a9`, `0x10ad`, `0x10b1` |
| Lignes IA | 3 | 3 | `localized-sampled-track-data` | high | Les trois lignes IA sont lues dans track_editor.sav ; leurs points caractéristiques ressortent dans track.data, avec alternance XY/YX selon les blocs runtime. | ai_line_1 `0x061d`, `0x0621`, `0x10a5`, `0x10a9`, `0x10ad`, `0x10b1` ; ai_line_2 `0x1ac9`, `0x24d9`, `0x24dd`, `0x24e1` ; ai_line_3 `0x2ffd`, `0x3b0d`, `0x3b11`, `0x3b15` |
| Checkpoints | 3 | 3 | `localized-runtime-records` | high | Les trois checkpoints sont présents dans track_editor.sav et correspondent aux records compacts de track.data. | Finish@0x004a, Checkpoint 1@0x002b, Checkpoint 2@0x000c |
| Pitlane | 1 | 1 | `localized-token-and-sampled-connectors` | medium | Le bâtiment pitlane est présent par token runtime ; les deux voies pit1/pit2 sont lues comme connecteurs vectoriels dans le .sav et échantillonnées dans track.data. | token `0x620d` ; pit1 `0x5465`, `0x55c5`, `0x56b5`, `0x56b9` ; pit2 `0x4365`, `0x4595`, `0x48fd` |
| Entrée de pitlane | 1 | 1 | `localized-sampled-track-data` | medium | La voie pit1 commence à 1565/826.9 dans le .sav et est retrouvée dans track.data. | runtime `0x5465`, `0x55c5`, `0x56b5`, `0x56b9` |
| Sortie de pitlane | 1 | 1 | `localized-sampled-track-data` | medium | La voie pit2 commence à 2819/826.9 dans le .sav ; ses coordonnées sont retrouvées dans track.data, surtout en stockage YX. | runtime `0x4365`, `0x4595`, `0x48fd` |
| Mur en plusieurs segments | 1 | 1 | `editor-vector-and-baked-runtime-raster` | medium | Le mur est vectoriel dans track_editor.sav ; dans le runtime jouable il est principalement validé par sa présence rasterisée dans track.png/track_preview.png. | `track.png` bbox [0, 0, 4096, 2048] |
| Zone de sable (polygone) | 1 | 1 | `editor-vector-and-runtime-layer` | high | Le polygone sable est vectoriel dans track_editor.sav et correspond au calque runtime gravel.png. | track.data `0x0c6d`, `0x5085` ; `gravel.png` bbox [1381, 1126, 1875, 1536] |
| Zone d'arbres (polygone) | 1 | 1 | `editor-vector-and-baked-runtime-raster` | medium | La zone d'arbres est vectorielle dans track_editor.sav ; le runtime la porte dans les rendus composites plutôt que dans un calque alpha isolable. | track.data `0x7518`, `0x7e48`, `0x8918`, `0x891c`, `0x8920` ; `track.png` bbox [0, 0, 4096, 2048] |

## Blocs vectoriels du track_editor.sav

| Offset | Points | Premier point | Dernier point |
| --- | ---: | --- | --- |
| `0x004d` | 5 | (1424.000, 1072.000) | (1424.000, 1072.000) |
| `0x015d` | 20 | (2204.248, 1092.000) | (1306.988, 1426.178) |
| `0x0290` | 8 | (1424.000, 1104.000) | (1424.000, 1104.000) |
| `0x04c8` | 11 | (1488.000, 624.000) | (1488.000, 624.000) |
| `0x06e6` | 8 | (2416.000, 1136.000) | (1520.000, 1616.000) |
| `0x0997` | 3 | (1565.000, 826.900) | (1359.417, 1094.691) |
| `0x0a43` | 5 | (2819.000, 826.900) | (2587.147, 1551.060) |
| `0x0b43` | 5 | (1424.000, 1072.000) | (1424.000, 1072.000) |
| `0x0c43` | 5 | (1424.000, 1098.250) | (1424.000, 1098.250) |
| `0x0d43` | 5 | (1424.000, 1045.750) | (1424.000, 1045.750) |

## Calques runtime

| Fichier | Taille image | Pixels alpha | BBox alpha |
| --- | --- | ---: | --- |
| `track.png` | [4096, 2048] | 8388608 | [0, 0, 4096, 2048] |
| `track_preview.png` | [768, 384] | 294912 | [0, 0, 768, 384] |
| `gravel.png` | [4096, 2048] | 153194 | [1381, 1126, 1875, 1536] |
| `grass.png` | [4096, 2048] | 7766457 | [0, 0, 4096, 2048] |
| `minimap.png` | [4096, 2048] | 633113 | [1272, 718, 3006, 1767] |

## Tokens lisibles

- `track_editor.sav` pertinents : `spr_road` @ `0x0008` ; `grass_1` @ `0x0019` ; `spr_sand` @ `0x026c` ; `spr_sand_edge` @ `0x0276` ; `forrest2` @ `0x0414` ; `spr_water_edge` @ `0x041d` ; `forrest2` @ `0x045c` ; `spr_water_edge` @ `0x0465` ; `forrest2` @ `0x04a4` ; `spr_water_edge` @ `0x04ad` ; `wall1` @ `0x06d8` ; `spr_checkpoint` @ `0x086d` ; `Finish` @ `0x089d` ; `checkpoint` @ `0x08a8` ; `spr_checkpoint` @ `0x08b7` ; `Checkpoint 1` @ `0x08e6` ; `checkpoint` @ `0x08f6` ; `spr_checkpoint` @ `0x0906` ; `Checkpoint 2` @ `0x0935` ; `checkpoint` @ `0x0945` ; `spr_pit_building_to_right` @ `0x0955`
- `track_editor.sav` candidats ASCII bruts : 34 chaînes, filtrées dans cette vue.
- `track.data` pertinents : `checkpoint` @ `0x0020`, `0x003f`, `0x005e`, `0x6247`, `0x6272`, `0x629d` ; `spr_checkpoint` @ `0x6243`, `0x626e`, `0x6299` ; `spr_pit_building_to_right` @ `0x620d`
- `track.data` candidats ASCII bruts : 269 chaînes, volontairement non listées car très bruitées.

## Notes

- H-S01b distingue volontairement la source vectorielle embarquée (`track_editor.sav`) des données runtime jouables (`track.data` et PNG).
- Les éléments route, IA, checkpoints et pitlane gardent des signaux exploitables dans `track.data`.
- Les surfaces et objets décoratifs sont bien présents dans le `.sav`, mais une partie est consommée côté runtime sous forme de calques/rendus raster.
- Ce résultat suffit pour démarrer H-S02 sans perdre l'information source : le lecteur runtime devra garder `track_editor.sav` comme source vectorielle quand il est disponible.

## Conclusion

On peut passer à H-S02, mais le lecteur runtime devra assumer une stratégie hybride : `track.data` pour les données jouables déjà échantillonnées, `track_info.data` pour les métadonnées, et `track_editor.sav` pour conserver les objets vectoriels quand le runtime les a seulement rasterisés.

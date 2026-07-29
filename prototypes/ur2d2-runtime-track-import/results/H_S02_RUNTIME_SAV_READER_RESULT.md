# H-S02 - Lecteur brut runtime .sav

- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2
- **Scénario :** H-S02
- **Statut :** ready-for-h03-route-and-overlay
- **Date :** 2026-07-29T20:02:39Z
- **Dossier piste :** `C:\Users\jerem\Documents\UnityProject\Automation-LAP\prototypes\ur2d2-runtime-track-import\fixtures\source\R00_runtime_track_2`
- **Sortie brute :** `UR2D2RuntimeTrackData` v0.1.0

## Décision du jalon

H-S02 est exploitable : le `.sav` fournit explicitement les candidats de simulation utiles, à savoir la piste principale, les voies de pitlane, les murs et les checkpoints.

## Fichiers source

| Fichier | Taille | SHA-256 court |
| --- | ---: | --- |
| `track_editor.sav` | 3655 | `4483667becae` |
| `track_info.data` | 345 | `d4c3941e1e05` |
| `track.png` | 4384020 | `0acb0d0e1578` |
| `track_preview.png` | 454654 | `8bbe6b2a69ff` |
| `grass.png` | 298927 | `79b7f4314d40` |
| `gravel.png` | 316747 | `cd162a57404b` |
| `minimap.png` | 59780 | `dc4a0f6e638e` |

## Synthèse

| Mesure | Valeur |
| --- | ---: |
| `vectorBlocks` | 10 |
| `closedVectorBlocks` | 6 |
| `openVectorBlocks` | 4 |
| `checkpoints` | 3 |
| `objectCandidates` | 11 |
| `relevantEditorTokens` | 21 |
| `imageLayersPresent` | 5 |

## Éléments de simulation retenus

| Élément | Statut | Offset | Points | Confiance | Raison |
| --- | --- | --- | ---: | --- | --- |
| Piste principale | trouvé | `0x004d` | 5 | high | Primary road vector trace from the .sav counted-array region. |
| pitlane-entry | trouvé | `0x0997` | 3 | medium | Open vector block following spr_pit_building_to_right; role assigned by order in the .sav. |
| pitlane-exit | trouvé | `0x0a43` | 5 | medium | Open vector block following spr_pit_building_to_right; role assigned by order in the .sav. |
| Mur | trouvé | `0x06e6` | 8 | high | Vector block located after a wall1 token. |

## Métadonnées track_info.data

- `First_Track`
- `track:2/2796.14`
- `flag_andorra`
- `ffffff`
- `Road Course`
- `medium`
- `soft`
- `clear`
- `[D.C.o.K] Magmort`

## Checkpoints

| Label | X | Y | Rotation | Payload |
| --- | ---: | ---: | ---: | --- |
| Finish | 2239.639 | 1072.000 | 270.000 | `0x087d` |
| Checkpoint 1 | 2368.645 | 1712.000 | 450.000 | `0x08c6` |
| Checkpoint 2 | 1356.068 | 1629.606 | 377.835 | `0x0915` |

## Tokens objets

| Token | Count |
| --- | ---: |
| `forrest2` | 3 |
| `spr_pit_building_to_right` | 1 |
| `spr_sand` | 2 |
| `spr_sand_edge` | 1 |
| `spr_water_edge` | 3 |
| `wall1` | 1 |

## Blocs vectoriels bruts conservés

| Offset | Points | Fermé | Longueur | Aire abs. | Token proche | Tags |
| --- | ---: | --- | ---: | ---: | --- | --- |
| `0x0d43` | 5 | oui | 3497.000 | 731280.000 | - | closed-vector-trace, coordinate-plausible, handles-present, closed-shape-candidate |
| `0x004d` | 5 | oui | 3392.000 | 675840.000 | grass_1 | closed-vector-trace, coordinate-plausible, handles-present, near-token:grass_1 |
| `0x0b43` | 5 | oui | 3392.000 | 675840.000 | - | closed-vector-trace, coordinate-plausible, handles-present, closed-shape-candidate |
| `0x0c43` | 5 | oui | 3287.000 | 620400.000 | - | closed-vector-trace, coordinate-plausible, handles-present, closed-shape-candidate |
| `0x04c8` | 11 | oui | 3168.584 | 380416.000 | spr_water_edge | closed-vector-trace, coordinate-plausible, handles-present, near-token:spr_water_edge |
| `0x0290` | 8 | oui | 1573.420 | 162816.000 | spr_sand_edge | closed-vector-trace, coordinate-plausible, handles-present, near-token:spr_sand_edge |
| `0x06e6` | 8 | non | 1434.932 | 241664.000 | wall1 | open-vector-trace, coordinate-plausible, handles-present, near-token:wall1 |
| `0x015d` | 20 | non | 1413.012 | 153634.041 | - | open-vector-trace, coordinate-plausible, line-candidate |
| `0x0a43` | 5 | non | 924.894 | 77990.930 | spr_pit_building_to_right | open-vector-trace, coordinate-plausible, handles-present, near-token:spr_pit_building_to_right |
| `0x0997` | 3 | non | 374.862 | 13421.037 | spr_pit_building_to_right | open-vector-trace, coordinate-plausible, handles-present, near-token:spr_pit_building_to_right |

## Calques PNG

| Fichier | Taille image | Pixels alpha | BBox alpha |
| --- | --- | ---: | --- |
| `track.png` | [4096, 2048] | 8388608 | [0, 0, 4096, 2048] |
| `track_preview.png` | [768, 384] | 294912 | [0, 0, 768, 384] |
| `grass.png` | [4096, 2048] | 7766457 | [0, 0, 4096, 2048] |
| `gravel.png` | [4096, 2048] | 153194 | [1381, 1126, 1875, 1536] |
| `minimap.png` | [4096, 2048] | 633113 | [1272, 718, 3006, 1767] |

## Garanties

- All offsets are byte offsets in the source track_editor.sav.
- Simulation features are read from track_editor.sav, not from track.data.
- The main track, pitlane lanes and walls are exposed as explicit feature candidates.
- track_info.data strings are cleaned as metadata hints only.
- PNG layers are treated as runtime background/raster evidence, not regenerated vector geometry.

Limites explicites :

- H-S02 does not convert editor units to metres.
- H-S02 does not align .sav coordinates to image pixels yet.
- Object payload schemas remain provisional.

## Prochaine étape

H-S03 peut maintenant convertir la piste principale, les voies de pitlane et les murs vers le repère de simulation, puis H-S04 les superposera au fond PNG runtime.

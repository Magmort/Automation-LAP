# G-S02 - Lecteur brut exploratoire UR2D2 .sav

- **Expérience :** G - Import du modèle minimal depuis les sauvegardes UR2D2
- **Scénario :** G-S02
- **Statut :** raw-reader-ready-for-g-s03-candidate-conversion
- **Date :** 2026-07-28T20:42:27+00:00
- **Fixtures analysées :** 8
- **Sortie brute :** `UR2D2RawTrackData` v0.1.0

## Décision du jalon

G-S02 est exploitable pour préparer une G-S03 vector-aware : le lecteur brut extrait une région stable de tableaux `float32` comptés, des clés vectorielles candidates, des objets/checkpoints candidats et conserve les régions inconnues.

## Schéma brut

- Offsets are source byte offsets in the .sav file.
- Values are decoded as little-endian float32 only where a stable counted-array or object-payload hypothesis exists.
- Unknown regions are retained explicitly and not silently discarded.

Limites explicites :

- No conversion to metres is performed.
- No axis, orientation or direction convention is finalized.
- Object payload layouts remain provisional.
- Vector handle interpolation formula remains provisional.

## Synthèse par fixture

| Fixture | Taille | Tableaux | Clés route | Points échantillonnés | Checkpoints candidats | Objets candidats | Région tableaux |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| T00_empty_save | 289 | 17 | 0 | 0 | 0 | 0 | `0x004d..0x0091` |
| T01_single_straight | 377 | 17 | 2 | 0 | 0 | 0 | `0x004d..0x00e9` |
| T02_simple_closed_loop | 749 | 17 | 5 | 20 | 0 | 0 | `0x004d..0x0261` |
| T03_ai_line | 1409 | 17 | 5 | 20 | 0 | 0 | `0x004d..0x0261` |
| T04_limits_or_walls | 1815 | 17 | 5 | 20 | 0 | 1 | `0x004d..0x0261` |
| T05_start_and_checkpoints | 2046 | 17 | 5 | 20 | 3 | 1 | `0x004d..0x0261` |
| T06_pit_lane | 2532 | 17 | 5 | 20 | 3 | 2 | `0x004d..0x0261` |
| T07_surfaces | 3655 | 17 | 5 | 20 | 3 | 11 | `0x004d..0x0261` |

## Inventaire des éléments attendus

- **Statut inventaire :** complete-with-low-confidence-pitlane-role-assignment

| Élément | Attendu | Détecté/lu | Statut | Confiance | Fixture | Preuve |
| --- | ---: | ---: | --- | --- | --- | --- |
| Segments de route | 4 | 4 | read | high | T02_simple_closed_loop | 5 control points, last point duplicates the first point. |
| Lignes IA | 3 | 3 | read | medium | T03_ai_line | Three line-like blocks added by T03 after the primary route block. |
| Checkpoints | 3 | 3 | read | medium | T05_start_and_checkpoints | spr_checkpoint payloads with labels Checkpoint 2, Checkpoint 1 and Finish. |
| Pitlane | 1 | 1 | detected | low | T06_pit_lane | spr_pit_building_to_right token plus pit connector line-like blocks; exact pitlane schema still provisional. |
| Entrée de pitlane | 1 | 1 | candidate | low | T06_pit_lane | First pit connector line-like block at 0x0534 with 3 points. |
| Sortie de pitlane | 1 | 1 | candidate | low | T06_pit_lane | Second pit connector line-like block at 0x05e0 with 5 points. |
| Mur en plusieurs segments | 1 | 1 | read | medium | T04_limits_or_walls | wall1 token followed by a 8-point line-like block. |
| Zone de sable (polygone) | 1 | 1 | read | medium | T07_surfaces | spr_sand token followed by a 8-point polygon-like block. |
| Zone d'arbres (polygone) | 1 | 1 | read | medium | T07_surfaces | forrest2 token followed by an 11-point polygon-like block. |

Notes :

- read = geometry payload is extracted as counted float arrays.
- detected = element token is present but full schema is not yet understood.
- candidate = geometry exists, but role assignment still needs confirmation in the editor/game.
- Pitlane entry and exit are assigned by order of the two connector-like blocks after spr_pit_building_to_right; this is low confidence.
- All route/AI/wall/surface geometries are vector trace candidates; the exact handle interpolation formula remains to validate.

## Tableaux identifiés

| Index | Nom provisoire | Confiance | Count | Offset | Extrait |
| ---: | --- | --- | ---: | --- | --- |
| 0 | `road_control_x` | high | 5 | `0x004d` | 1424.0, 2480.0, 2480.0, 1424.0, 1424.0 |
| 1 | `road_control_y` | high | 5 | `0x0065` | 1072.0, 1072.0, 1712.0, 1712.0, 1072.0 |
| 2 | `road_node_flags_or_types` | low | 5 | `0x007d` | 1.0, 1.0, 1.0, 1.0, 0.0 |
| 3 | `road_angle_a_deg` | medium | 5 | `0x0095` | -0.0, -0.0, 180.0, 180.0, 0.0 |
| 4 | `road_angle_b_deg` | medium | 5 | `0x00ad` | 180.0, -0.0, -0.0, 180.0, 0.0 |
| 5 | `road_handle_weight_a` | medium | 5 | `0x00c5` | 130.0, 130.0, 128.0, 130.0, 0.0 |
| 6 | `road_handle_weight_b` | medium | 5 | `0x00dd` | 130.0, 130.0, 130.0, 130.0, 0.0 |
| 7 | `generated_edge_or_mesh_x` | medium | 10 | `0x00f5` | 1554.0, 2350.0, 2610.0, 2610.0, 2352.0, 1554.0, 1294.0, 1294.0, ... |
| 8 | `generated_edge_or_mesh_y` | medium | 10 | `0x0121` | 1072.0, 1072.0, 1072.0, 1712.0, 1712.0, 1712.0, 1712.0, 1072.0, ... |
| 9 | `unknown_counted_float_array_09` | low | 0 | `0x014d` |  |
| 10 | `unknown_counted_float_array_10` | low | 0 | `0x0151` |  |
| 11 | `unknown_counted_float_array_11` | low | 0 | `0x0155` |  |
| 12 | `unknown_counted_float_array_12` | low | 0 | `0x0159` |  |
| 13 | `sampled_line_x` | medium | 20 | `0x015d` | 2204.248291, 2160.88916, 2077.271973, 2035.885254, 1952.0, 1909.946167, 1826.728027, 1786.008545, ... |
| 14 | `sampled_line_y` | medium | 20 | `0x01b1` | 1092.0, 1052.0, 1092.0, 1052.0, 1092.0, 1052.0, 1092.0, 1052.0, ... |
| 15 | `sampled_line_angle_deg` | low | 20 | `0x0205` | -0.0, -0.0, -0.0, -0.0, -0.0, -0.0, -0.0, -0.0, ... |
| 16 | `unknown_scalar_block` | low | 1 | `0x0259` | 1.0 |

## Checkpoints candidats

| Fixture | Label | X | Y | Rotation | Payload |
| --- | --- | ---: | ---: | ---: | --- |
| T05_start_and_checkpoints | Checkpoint 2 | 1356.068115 | 1629.605835 | 377.834503 | `0x041a` |
| T05_start_and_checkpoints | Checkpoint 1 | 2368.644531 | 1712.0 | 450.0 | `0x0469` |
| T05_start_and_checkpoints | Finish | 2239.638916 | 1072.0 | 270.0 | `0x04b8` |

## Interprétation provisoire

- Les tableaux 0 et 1 forment les positions de clés de route candidates en unités éditeur.
- Les tableaux 3 et 4 ressemblent à des angles de poignées vectorielles ; les tableaux 5 et 6 ressemblent à des poids de poignées.
- Le `float32` global initial `10.0` devient le meilleur candidat de largeur de route pour `TrackDefinition` v0.1.
- Les checkpoints sont présents avec positions et rotations plausibles dans T05.
- Les objets murs, stands et surfaces sont détectables par token, mais leur payload exact reste moins fiable que celui des checkpoints.
- La conversion G-S03 doit échantillonner les courbes vectorielles, pas seulement relier les clés par segments droits.

# G-S01 - Analyse différentielle initiale des sauvegardes UR2D2

- **Expérience :** G - Import du modèle minimal depuis UR2D2
- **Scénario :** G-S01
- **Statut :** valid-for-g-s02-probing
- **Date :** 2026-07-28T18:27:10+00:00
- **Dossier analysé :** `C:\Users\jerem\Documents\UnityProject\Automation-LAP\prototypes\ur2d2-track-import\fixtures\source`
- **Fixtures analysées :** 8 / 8
- **Nature des fichiers :** sauvegardes `.sav` directement issues de l'éditeur, pas exports finaux de piste

## Synthèse

- Les sauvegardes .sav ne semblent pas compressées : chaînes lisibles et entropie basse à moyenne observées en G-S00.
- Le fichier commence par un float32 little-endian valant 10.0, candidat pour une largeur, échelle ou paramètre global.
- Les étapes ajoutent des blocs lisibles liés aux familles d'objets attendues : wall1, spr_checkpoint, checkpoint, spr_pit_building_to_right, surfaces.
- La géométrie de route apparaît avant les objets décoratifs/fonctionnels et contient des float32 plausibles, dont -48.0 dès T01.

## Taille et chaînes lisibles

| Fixture | Taille | Chaînes lisibles principales |
| --- | ---: | --- |
| T00_empty_save | 289 | `spr_road`@0x0008, `grass_1`@0x0019 |
| T01_single_straight | 377 | `spr_road`@0x0008, `grass_1`@0x0019 |
| T02_simple_closed_loop | 749 | `spr_road`@0x0008, `grass_1`@0x0019 |
| T03_ai_line | 1409 | `spr_road`@0x0008, `grass_1`@0x0019, `@l%4C`@0x03e0, ` !ES`@0x0436, ` ANS`@0x0453, `C3d4C`@0x04ec |
| T04_limits_or_walls | 1815 | `spr_road`@0x0008, `grass_1`@0x0019, `wall1`@0x0275, `@l%4C`@0x0576, ` !ES`@0x05cc, ` ANS`@0x05e9, `C3d4C`@0x0682 |
| T05_start_and_checkpoints | 2046 | `spr_road`@0x0008, `grass_1`@0x0019, `wall1`@0x0275, `@@spr_checkpoint`@0x0409, `Checkpoint 2`@0x043a, `@checkpoint`@0x044a, `spr_checkpoint`@0x045a, `Checkpoint 1`@0x0489 |
| T06_pit_lane | 2532 | `spr_road`@0x0008, `grass_1`@0x0019, `wall1`@0x0275, `@spr_pit_building_to_right`@0x040a, `spr_checkpoint`@0x0449, `Checkpoint 2`@0x0478, `@checkpoint`@0x0488, `spr_checkpoint`@0x0498 |
| T07_surfaces | 3655 | `spr_road`@0x0008, `grass_1`@0x0019, `@forrest2`@0x026c, `spr_water_edge`@0x0276, `{CYO`@0x0333, `*D/w%D`@0x0443, `$D-w`@0x048b, `forrest2`@0x0499 |

## Deltas successifs

| Transition | Delta | Préfixe commun | Suffixe commun | Zone nouvelle | Chaînes nouvelles | Candidats float32 |
| --- | ---: | ---: | ---: | --- | --- | --- |
| T00_empty_save -> T01_single_straight | 88 | 80 | 184 | `0x0050..0x00c1` (113 o) | - | 1424.0@0x0051, 2480.0@0x0055, 2.0@0x0059, 1072.0@0x005d, 1072.0@0x0061, 2.0@0x0065 |
| T01_single_straight -> T02_simple_closed_loop | 372 | 79 | 0 | `0x004f..0x02ed` (670 o) | - | 1424.0@0x0051, 2480.0@0x0055, 2480.0@0x0059, 1424.0@0x005d, 1424.0@0x0061, 5.0@0x0065 |
| T02_simple_closed_loop -> T03_ai_line | 660 | 55 | 4 | `0x0037..0x057d` (1350 o) | `@l%4C`@0x03e0, ` !ES`@0x0436, ` ANS`@0x0453, `C3d4C`@0x04ec | 105.0@0x0039, 12.5@0x003d, 4096.0@0x0041, 2048.0@0x0045, 5.0@0x004d, 1424.0@0x0051 |
| T03_ai_line -> T04_limits_or_walls | 406 | 623 | 786 | `0x026f..0x0405` (406 o) | `wall1`@0x0275 | 2.0@0x027a, 12.0@0x027b, -1.0@0x027f, 8.0@0x0283, 2416.0@0x0287, 2480.0@0x028b |
| T04_limits_or_walls -> T05_start_and_checkpoints | 231 | 75 | 785 | `0x004b..0x04ed` (1186 o) | `wall1`@0x0275, `@@spr_checkpoint`@0x0409, `Checkpoint 2`@0x043a, `@checkpoint`@0x044a, `spr_checkpoint`@0x045a | 5.0@0x004d, 1424.0@0x0051, 2480.0@0x0055, 2480.0@0x0059, 1424.0@0x005d, 1424.0@0x0061 |
| T05_start_and_checkpoints -> T06_pit_lane | 486 | 1033 | 780 | `0x0409..0x06d8` (719 o) | `@spr_pit_building_to_right`@0x040a, `spr_checkpoint`@0x0449, `Checkpoint 2`@0x0478, `@checkpoint`@0x0488, `spr_checkpoint`@0x0498 | 2192.0@0x0425, 720.0@0x0429, -1.0@0x042d, 90.0@0x0431, 1.0@0x0435, 1.0@0x0439 |
| T06_pit_lane -> T07_surfaces | 1123 | 619 | 948 | `0x026b..0x0a93` (2088 o) | `@forrest2`@0x026c, `spr_water_edge`@0x0276, `{CYO`@0x0333, `*D/w%D`@0x0443, `$D-w`@0x048b | 1.0@0x0285, 8.0@0x0289, 2.000015@0x028c, -3.0@0x028d, 11.0@0x0291, -0.000488@0x0294 |

## Interprétation provisoire

- Les fixtures sont suffisantes pour commencer G-S02 sur un lecteur brut exploratoire.
- La prochaine cible est d'isoler la table de route avec T00/T01/T02, puis la table d'objets avec T04/T05/T06/T07.
- Aucune transformation vers `TrackDefinition` ne doit encore être figée : les offsets et structures restent hypothétiques.

# G-S00 - Inventaire des fichiers UR2D2

- **Expérience :** G - Import du modèle minimal depuis UR2D2
- **Scénario :** G-S00
- **Statut :** complete-inventory
- **Date :** 2026-07-28T18:24:33+00:00
- **Dossier analysé :** `C:\Users\jerem\Documents\UnityProject\Automation-LAP\prototypes\ur2d2-track-import\fixtures\source`
- **Fixtures observées :** 8 / 8

## Couverture

| Fixture | Présente | Fichiers | Taille totale | Signatures |
| --- | --- | ---: | ---: | --- |
| T00_empty_save | oui | 1 | 289 | unknown-binary: 1 |
| T01_single_straight | oui | 1 | 377 | unknown-binary: 1 |
| T02_simple_closed_loop | oui | 1 | 749 | unknown-binary: 1 |
| T03_ai_line | oui | 1 | 1409 | unknown-binary: 1 |
| T04_limits_or_walls | oui | 1 | 1815 | unknown-binary: 1 |
| T05_start_and_checkpoints | oui | 1 | 2046 | unknown-binary: 1 |
| T06_pit_lane | oui | 1 | 2532 | unknown-binary: 1 |
| T07_surfaces | oui | 1 | 3655 | unknown-binary: 1 |

## Comparaisons successives

| De | Vers | Ajoutés | Modifiés | Supprimés | Inchangés |
| --- | --- | ---: | ---: | ---: | ---: |
| T00_empty_save | T01_single_straight | 0 | 1 | 0 | 0 |
| T01_single_straight | T02_simple_closed_loop | 0 | 1 | 0 | 0 |
| T02_simple_closed_loop | T03_ai_line | 0 | 1 | 0 | 0 |
| T03_ai_line | T04_limits_or_walls | 0 | 1 | 0 | 0 |
| T04_limits_or_walls | T05_start_and_checkpoints | 0 | 1 | 0 | 0 |
| T05_start_and_checkpoints | T06_pit_lane | 0 | 1 | 0 | 0 |
| T06_pit_lane | T07_surfaces | 0 | 1 | 0 | 0 |

## Indices initiaux

- Fichiers binaires inconnus à forte entropie : 0
- Fichiers ou échantillons contenant des chaînes lisibles : 8

### Exemples de chaînes lisibles

- `T00_empty_save/track.sav` (unknown-binary) : spr_road ; grass_1
- `T01_single_straight/track.sav` (unknown-binary) : spr_road ; grass_1
- `T02_simple_closed_loop/track.sav` (unknown-binary) : spr_road ; grass_1
- `T03_ai_line/track.sav` (unknown-binary) : spr_road ; grass_1 ; @l%4C ; !ES ; ANS
- `T04_limits_or_walls/track.sav` (unknown-binary) : spr_road ; grass_1 ; wall1 ; @l%4C ; !ES
- `T05_start_and_checkpoints/track.sav` (unknown-binary) : spr_road ; grass_1 ; wall1 ; @@spr_checkpoint ; Checkpoint 2
- `T06_pit_lane/track.sav` (unknown-binary) : spr_road ; grass_1 ; wall1 ; @spr_pit_building_to_right ; spr_checkpoint
- `T07_surfaces/track.sav` (unknown-binary) : spr_road ; grass_1 ; @forrest2 ; spr_water_edge ; {CYO

## Prochaine étape

Quand au moins T00 et T01 sont présents, l'inventaire peut alimenter G-S01 pour isoler les structures modifiées par la géométrie.

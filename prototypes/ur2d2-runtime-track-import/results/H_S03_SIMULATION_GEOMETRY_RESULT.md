# H-S03 - Géométrie de simulation depuis .sav

- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2
- **Scénario :** H-S03
- **Statut :** validated-with-reserves
- **Date :** 2026-07-29T20:15:56Z
- **TrackDefinition :** `C:\Users\jerem\Documents\UnityProject\Automation-LAP\prototypes\ur2d2-runtime-track-import\results\h_s03_track_definition_candidate.json`
- **Validation C-S01 :** succès

## Décision du jalon

H-S03 produit une géométrie de simulation exploitable : la piste principale du `.sav` est convertie en `TrackDefinition` v0.1 et passe C-S01.

## Conversion

- Source piste : `0x004d`.
- Échelle : `1 m = 12.8 unités éditeur` (`reused-from-g-grid-calibration`).
- Largeur piste : 10.000 m total.
- Axes : raw editor x increases to simulation x ; raw editor y is inverted so screen-down editor coordinates become negative forward coordinates.
- Vectoriel : 16 échantillons par segment ; cubic Bezier per vector segment using angleA/weightA as outgoing handle and angleB/weightB as incoming handle on the same source row.
- Pitlane : 2 voies converties hors contrat C.
- Murs : 1 polylignes converties hors contrat C.

## Validation C-S01

- Erreurs : 0
- Points : 64
- Segments : 64
- Longueur : 275.352 m
- Largeur totale min : 10.000 m
- Courbure max absolue : 0.241360 1/m

## Éléments convertis

| Élément | Count | Longueur |
| --- | ---: | ---: |
| Centerline | 64 | 275.352 m |
| Pitlane | 2 | 103.028 m |
| Murs | 1 | 112.375 m |
| Checkpoints | 3 | - |

## Réserves

- H-S03 does not align coordinates to PNG pixels yet.
- H-S03 does not simulate a vehicle yet.
- H-S03 does not encode pitlane or walls into TrackDefinition v0.1 because C's contract does not include them.

## Prochaine étape

H-S04 doit superposer cette géométrie convertie au fond PNG runtime afin de valider l'alignement image/coordonnées.

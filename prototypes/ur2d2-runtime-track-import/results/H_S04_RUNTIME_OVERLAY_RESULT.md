# H-S04 - Superposition sur fond runtime

- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2
- **Scénario :** H-S04
- **Statut :** overlay-ready
- **Date :** 2026-07-29T20:29:44Z
- **Visualisation :** `C:\Users\jerem\Documents\UnityProject\Automation-LAP\prototypes\ur2d2-runtime-track-import\results\H_S04_RUNTIME_OVERLAY_VISUALIZATION.svg`

## Décision du jalon

H-S04 est prête pour validation visuelle : les coordonnées `.sav` peuvent être superposées au fond `track_preview.png` avec une échelle uniforme.

## Contrôles

| Contrôle | Résultat |
| --- | --- |
| `backgroundPreviewPresent` | oui |
| `aspectRatioMatchesTrackPng` | oui |
| `uniformPreviewScale` | oui |
| `featureBoundsInsideTrackCanvas` | oui |
| `trackFeaturePresent` | oui |
| `pitlaneLanesPresent` | oui |
| `wallPresent` | oui |
| `checkpointsPresent` | oui |
| `hS03TrackDefinitionValid` | oui |

## Mapping

- Fond : `C:\Users\jerem\Documents\UnityProject\Automation-LAP\prototypes\ur2d2-runtime-track-import\fixtures\source\R00_runtime_track_2\track_preview.png`
- Image source : 4096 x 2048 px
- Preview : 768 x 384 px
- Échelle preview : x `0.187500`, y `0.187500`
- Largeur piste : 10.000 m -> 24.000 px preview
- Largeur pitlane : 5.000 m -> 12.000 px preview

## Géométrie superposée

- Piste : `0x004d`
- Pitlane : `0x0997`, `0x0a43`
- Murs : `0x06e6`
- Checkpoints : Finish, Checkpoint 1, Checkpoint 2

## Notes

- H-S04 uses raw editor/screen coordinates for overlay, so Y points down like UR2D2 images.
- The SVG embeds track_preview.png and overlays vector-sampled .sav features.
- H-S04 does not run vehicle simulation; that remains H-S06.

## Prochaine étape

Après validation visuelle, H-S05 pourra préparer la conversion finale `TrackDefinition`/données hors contrat pour la simulation fonctionnelle.

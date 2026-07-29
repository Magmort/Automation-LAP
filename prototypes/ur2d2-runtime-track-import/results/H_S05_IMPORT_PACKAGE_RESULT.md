# H-S05 - Paquet d'import simulation

- **Expérience :** H - Import depuis les vrais fichiers de tracks UR2D2
- **Scénario :** H-S05
- **Statut :** import-package-ready-for-h-s06
- **Date :** 2026-07-29T20:40:17Z
- **Package :** `C:\Users\jerem\Documents\UnityProject\Automation-LAP\prototypes\ur2d2-runtime-track-import\results\h_s05_import_package.json`
- **SHA-256 contenu :** `476eb2a68c2fe2ac`

## Décision du jalon

H-S05 consolide un paquet d'import prêt pour la simulation : `TrackDefinition` valide, données hors contrat utiles et mapping runtime PNG sont réunis sans dépendre de `track.data`.

## Contrôles

| Contrôle | Résultat |
| --- | --- |
| `trackDefinitionValid` | oui |
| `overlayValidated` | oui |
| `trackDataNotRequired` | oui |
| `pitlaneIncluded` | oui |
| `wallsIncluded` | oui |
| `backgroundIncluded` | oui |
| `uniformPixelMapping` | oui |

## Contenu

| Élément | Valeur |
| --- | ---: |
| Points centerline | 64 |
| Longueur | 275.352 m |
| Largeur min | 10.000 m |
| Voies pitlane | 2 |
| Murs | 1 |
| Checkpoints | 3 |

## Rendu runtime

- Fond préféré : `track_preview.png`
- Mapping : `track_editor.sav raw editor coordinates` -> `track_preview.png pixels`
- Échelle : x `0.187500`, y `0.187500`
- Axe Y : `down`

## Provenance

- `.sav` : `track_editor.sav`
- `track_info.data` : `track_info.data`
- `track.data` utilisé : non

## Réserves

- The package references UR2D2 image assets by local path; it does not redistribute them.
- Pitlane and walls are outside TrackDefinition v0.1 and must be consumed from simulationExtras.
- Vehicle simulation and replay rendering are not performed in H-S05.

## Prochaine étape

H-S06 can run the autonomous vehicle on the packaged TrackDefinition and render it over the runtime background.

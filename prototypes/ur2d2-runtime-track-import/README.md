# Expérience H - Import des vrais fichiers de tracks UR2D2

Ce prototype vérifie si les fichiers de piste finis d'Ultimate Racing 2D 2 peuvent alimenter le `TrackDefinition` v0.1 validé par l'expérience C.

H est séparée de G :

- G analyse les sauvegardes `.sav` du Track Editor ;
- H analyse les fichiers de piste réellement utilisés ou exportés par UR2D2.

## Objectif immédiat

H-S00 produit un inventaire reproductible des packages ou dossiers de pistes :

- composition des fichiers ;
- tailles et empreintes SHA-256 ;
- signatures binaires ;
- indices de compression ou d'archive ;
- chaînes lisibles ;
- visualisation de couverture.

## Données attendues

Les fichiers source UR2D2 ne doivent pas être committés s'ils ne sont pas redistribuables.

Par défaut, l'outil cherche les fixtures dans :

```text
prototypes/ur2d2-runtime-track-import/fixtures/source/
```

Structure recommandée :

```text
source/
  R00_simple_export/
  R01_start_and_checkpoints/
  R02_limits_or_walls/
  R03_surfaces/
  R04_real_track_sample/
```

Chaque entrée peut être un dossier complet ou un fichier unique.

## Exécution

```powershell
python prototypes\ur2d2-runtime-track-import\tools\run_h_s00_runtime_inventory.py
python prototypes\ur2d2-runtime-track-import\tools\render_h_s00_runtime_inventory_visualization.py
python prototypes\ur2d2-runtime-track-import\tools\run_h_s01_runtime_g_comparison.py
python prototypes\ur2d2-runtime-track-import\tools\render_h_s01_runtime_g_comparison.py
python prototypes\ur2d2-runtime-track-import\tools\run_h_s01_runtime_element_inventory.py
python prototypes\ur2d2-runtime-track-import\tools\render_h_s01_runtime_element_inventory.py
python prototypes\ur2d2-runtime-track-import\tools\run_h_s02_runtime_sav_reader.py
python prototypes\ur2d2-runtime-track-import\tools\render_h_s02_runtime_sav_reader.py
python prototypes\ur2d2-runtime-track-import\tools\run_h_s03_sav_to_simulation_geometry.py
python prototypes\ur2d2-runtime-track-import\tools\render_h_s03_simulation_geometry.py
python prototypes\ur2d2-runtime-track-import\tools\run_h_s04_runtime_overlay.py
python prototypes\ur2d2-runtime-track-import\tools\render_h_s04_runtime_overlay.py
python prototypes\ur2d2-runtime-track-import\tools\run_h_s05_import_package.py
python prototypes\ur2d2-runtime-track-import\tools\render_h_s05_import_package.py
python prototypes\ur2d2-runtime-track-import\tools\run_h_s06_functional_replay.py
python prototypes\ur2d2-runtime-track-import\tools\render_h_s06_functional_replay.py
```

Il est aussi possible de pointer vers un dossier externe :

```powershell
python prototypes\ur2d2-runtime-track-import\tools\run_h_s00_runtime_inventory.py --fixtures-root "C:\chemin\vers\tracks"
```

## Résultats

Les résultats sont écrits dans :

```text
prototypes/ur2d2-runtime-track-import/results/
```

## Résultat courant

- H-S00 : inventaire runtime disponible pour `R00_runtime_track_2`.
- H-S01 : comparaison G/H validée ; `track.data` contient les clés route et checkpoints corrélables avec G.
- H-S01b : inventaire exhaustif validé ; les 4 segments de route, 3 lignes IA, 3 checkpoints, pitlane, entrée/sortie de pitlane, mur, sable et arbres sont localisés dans le package runtime.
- H-S02 : lecteur `.sav` single-track validé ; `UR2D2RuntimeTrackData` v0.1 expose la piste principale, les voies de pitlane, les murs et les checkpoints depuis `track_editor.sav`, avec `track_info.data` pour les métadonnées et les PNG comme fonds visuels.
- H-S03 : conversion `.sav` vers géométrie de simulation validée ; le `TrackDefinition` v0.1 passe C-S01 avec 64 points, 275,352 m de longueur et 10 m de largeur.
- H-S04 : superposition `.sav` sur `track_preview.png` validée visuellement ; échelle uniforme 0,1875, largeur piste/pitlane correcte, piste/pitlane/mur/checkpoints alignés dans le canvas.
- H-S05 : paquet d'import simulation prêt pour H-S06 ; `TrackDefinition` valide, données hors contrat utiles, mapping runtime PNG et provenance sont consolidés sans dépendre de `track.data`.
- H-S06 : replay fonctionnel prêt pour validation visuelle ; la QFC55 parcourt 3 tours sur le `TrackDefinition` H-S05 avec le contrôleur C-S03, sans sortie de piste, puis la trajectoire est affichée sur le fond runtime.
- Prochaine étape : valider visuellement H-S06, puis décider si H peut être clôturée ou prolongée avec des scénarios murs/pitlane.

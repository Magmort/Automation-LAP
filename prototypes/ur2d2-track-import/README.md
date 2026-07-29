# Expérience G - Import UR2D2

Ce prototype vérifie si les fichiers produits par le Track Editor d'Ultimate Racing 2D 2 permettent de reconstruire le `TrackDefinition` v0.1 validé par l'expérience C.

## Objectif immédiat

G-S00 ne tente pas encore de décoder le format. Le jalon produit un inventaire reproductible :

- fichiers observés par fixture ;
- tailles, dates et empreintes SHA-256 ;
- signatures binaires et indices de compression ;
- chaînes lisibles ;
- différences entre fixtures successives ;
- visualisation simple de couverture.

## Données attendues

Les fichiers source UR2D2 ne doivent pas être committés s'ils ne sont pas redistribuables.

Par défaut, l'outil cherche les fixtures dans :

```text
prototypes/ur2d2-track-import/fixtures/source/
```

Structure attendue :

```text
source/
  T00_empty_save/
  T01_single_straight/
  T02_simple_closed_loop/
  T03_ai_line/
  T04_limits_or_walls/
  T05_start_and_checkpoints/
  T06_pit_lane/
  T07_surfaces/
```

Chaque dossier doit contenir la copie complète des fichiers produits ou modifiés par l'éditeur pour ce cas. Pour une première passe, l'outil accepte aussi les sauvegardes directes sous forme de fichiers `.sav` nommés `T00_empty_save.sav`, `T01_single_straight.sav`, etc.

## Exécution

```powershell
python prototypes\ur2d2-track-import\tools\run_g_s00_inventory.py
python prototypes\ur2d2-track-import\tools\render_g_s00_inventory_visualization.py
python prototypes\ur2d2-track-import\tools\run_g_s01_differential_analysis.py
python prototypes\ur2d2-track-import\tools\render_g_s01_differential_visualization.py
python prototypes\ur2d2-track-import\tools\run_g_s02_raw_reader.py
python prototypes\ur2d2-track-import\tools\render_g_s02_raw_reader_visualization.py
python prototypes\ur2d2-track-import\tools\run_g_s03_track_definition_conversion.py
python prototypes\ur2d2-track-import\tools\render_g_s03_track_definition_visualization.py
python prototypes\ur2d2-track-import\tools\run_g_s04_visual_validation.py
python prototypes\ur2d2-track-import\tools\render_g_s04_visual_validation.py
python prototypes\ur2d2-track-import\tools\render_g_s04_handle_interpretation.py
python prototypes\ur2d2-track-import\tools\render_g_s04_sand_handle_hypotheses.py
```

Il est aussi possible de pointer vers un dossier externe :

```powershell
python prototypes\ur2d2-track-import\tools\run_g_s00_inventory.py --fixtures-root "C:\chemin\vers\fixtures"
```

## Résultats

Les résultats sont écrits dans :

```text
prototypes/ur2d2-track-import/results/
```

Les fichiers source restent séparés des preuves committables.

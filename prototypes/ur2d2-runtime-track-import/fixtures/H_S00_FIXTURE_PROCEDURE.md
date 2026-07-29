# H-S00 - Procédure de collecte des vrais fichiers de tracks UR2D2

## But

Collecter les fichiers finaux ou runtime de pistes UR2D2, distincts des sauvegardes `.sav` du Track Editor analysées par G.

## Informations à noter

Pour chaque fixture, noter localement :

- version d'Ultimate Racing 2D 2 ;
- provenance : export final, dossier runtime local, piste exemple ou piste créée pour test ;
- chemin source original ;
- nom de piste visible en jeu ;
- date de génération ou modification ;
- relation éventuelle avec une fixture G.

## Arborescence cible

Déposer les fichiers ou dossiers dans :

```text
prototypes/ur2d2-runtime-track-import/fixtures/source/
  R00_simple_export/
  R01_start_and_checkpoints/
  R02_limits_or_walls/
  R03_surfaces/
  R04_real_track_sample/
```

Chaque entrée peut être :

- un dossier contenant tous les fichiers d'une piste ;
- un fichier unique si UR2D2 produit une piste sous forme d'un seul package.

## Séquence recommandée

1. **R00_simple_export** : exporter ou récupérer le vrai fichier de track correspondant à une boucle simple.
2. **R01_start_and_checkpoints** : utiliser une piste avec départ et checkpoints.
3. **R02_limits_or_walls** : utiliser une piste avec limites ou murs.
4. **R03_surfaces** : utiliser une piste avec surfaces distinctes.
5. **R04_real_track_sample** : ajouter une piste réelle ou exemple fourni par le jeu.

## Contraintes

- Ne pas committer les fichiers source UR2D2 s'ils ne sont pas redistribuables.
- Conserver les noms originaux des fichiers internes.
- Ne pas supprimer les miniatures, métadonnées ou fichiers annexes.
- Relancer H-S00 après chaque ajout.

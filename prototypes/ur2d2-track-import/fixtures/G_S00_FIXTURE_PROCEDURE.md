# G-S00 - Procédure de création des fixtures UR2D2

## But

Produire une série de dossiers différentiels où chaque sauvegarde ne change qu'une famille d'information. Cette série permet d'identifier quels fichiers et quelles zones binaires portent la géométrie, les limites, les lignes IA, le départ, les checkpoints, les stands et les surfaces.

## Informations à noter

Pour chaque fixture, noter dans un fichier local non obligatoire :

- version exacte d'Ultimate Racing 2D 2 ;
- version ou date du Track Editor si visible ;
- chemin source original ;
- date et heure de sauvegarde ;
- manipulation réalisée ;
- observation visuelle utile ;
- tout fichier supprimé ou régénéré manuellement.

## Arborescence cible

Créer ou copier les dossiers dans :

```text
prototypes/ur2d2-track-import/fixtures/source/
  T00_empty_save/
  T01_single_straight/
  T02_simple_closed_loop/
  T03_ai_line/
  T04_limits_or_walls/
  T05_start_and_checkpoints/
  T06_pit_lane/
  T07_surfaces/
```

Les noms exacts des sous-dossiers sont importants pour obtenir une comparaison automatique ordonnée.

Pour une première analyse limitée aux sauvegardes de l'éditeur, les fichiers `.sav` peuvent aussi être déposés directement dans `source/` :

```text
source/
  T00_empty_save.sav
  T01_single_straight.sav
  T02_simple_closed_loop.sav
  T03_ai_line.sav
  T04_limit_or_walls.sav
  T05_start_and_checkpoints.sav
  T06_pit_lane.sav
  T07_surfaces.sav
```

Dans ce mode, l'inventaire normalise chaque sauvegarde en `track.sav` pour comparer les contenus entre fixtures.

## Séquence recommandée

1. **T00_empty_save** : créer un nouveau circuit vide, l'enregistrer, puis copier le dossier complet produit par l'éditeur.
2. **T01_single_straight** : repartir de T00, ajouter une route droite simple, enregistrer, copier le dossier complet.
3. **T02_simple_closed_loop** : repartir de T01, fermer une boucle simple, enregistrer, copier le dossier complet.
4. **T03_ai_line** : repartir de T02, ajouter uniquement une ligne IA, enregistrer, copier le dossier complet.
5. **T04_limits_or_walls** : repartir de T03, ajouter uniquement limites, murs ou largeurs selon les outils disponibles, enregistrer, copier le dossier complet.
6. **T05_start_and_checkpoints** : repartir de T04, ajouter uniquement départ et checkpoints, enregistrer, copier le dossier complet.
7. **T06_pit_lane** : repartir de T05, ajouter uniquement une voie des stands si disponible, enregistrer, copier le dossier complet.
8. **T07_surfaces** : repartir de T06, ajouter uniquement une surface distincte, enregistrer, copier le dossier complet.

## Variante minimale

Si le Track Editor ne permet pas de créer tous les éléments, fournir au minimum :

- T00_empty_save ;
- T01_single_straight ;
- T02_simple_closed_loop ;
- T05_start_and_checkpoints.

Cette variante suffit pour commencer l'identification de la géométrie et du chronométrage.

## Contraintes

- Ne pas committer les fichiers UR2D2 source s'ils contiennent des assets non redistribuables.
- Ne pas modifier plusieurs familles d'information dans une même fixture.
- Ne pas renommer les fichiers internes produits par l'éditeur.
- Conserver les fichiers de métadonnées et miniatures, même s'ils semblent inutiles.
- Relancer l'inventaire après chaque ajout de fixture.

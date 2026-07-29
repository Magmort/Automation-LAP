# G-S04 - Validation visuelle de la conversion UR2D2

- **Expérience :** G - Import du modèle minimal depuis les sauvegardes UR2D2
- **Scénario :** G-S04
- **Statut :** validated-with-reserves
- **Date :** 2026-07-29T17:01:22+00:00
- **Visualisation :** `C:\Users\jerem\Documents\UnityProject\Automation-LAP\prototypes\ur2d2-track-import\results\G_S04_VISUAL_VALIDATION.svg`

## Décision du jalon

G-S04 valide visuellement la cohérence interne de la conversion et autorise le passage à G-S05 avec réserves.

## Couches affichées

- Clés vectorielles de route : 4
- Lignes IA : 3
- Checkpoints : 3
- Mur multi-segments : 1
- Connecteurs pitlane candidats : 2
- Segment pitlane droit : 1
- Polygone sable : 1
- Polygone arbres : 1

## Contrôles

- Validation C-S01 : pass
- Couches requises : pass

| Contrôle | Statut | Écart |
| --- | --- | ---: |
| top-straight | pass | 0.000000 m |
| bottom-straight | pass | 0.000000 m |

## Projection des checkpoints

| Checkpoint | Point projeté | Point le plus proche | Distance | Statut |
| --- | --- | --- | ---: | --- |
| checkpoint-2 | p13 | p13 | 1.434 m | pass |
| checkpoint-1 | p09 | p09 | 6.982 m | reserve |
| finish | p03 | p03 | 3.031 m | pass |

## Réserves

- La largeur de route est visuellement recalibrée à 5 m au total après retour utilisateur : 10 m rendait la piste presque deux fois trop large.
- pit1 est confirmé comme voie d'entrée des stands, pit2 comme voie de sortie, et la pitlane manquante est représentée par le segment droit entre les deux.
- Les lignes IA, le mur, les connecteurs pitlane, le sable et les arbres sont visualisés depuis les blocs bruts, mais ne font pas encore partie de TrackDefinition v0.1.
- La poignée B est maintenant interprétée comme la poignée entrante de la clé suivante : B visible sur Ki provient de la ligne Ki-1.
- Les vecteurs de poignées utilisent une inversion verticale globale par rapport aux coordonnées brutes des points.
- La convention d'index et de repère des poignées rétablit l'alignement tangent, mais reste à confirmer visuellement sur toutes les familles de tracés.
- Aucune capture de l'éditeur n'est disponible ; G-S04 valide donc la cohérence interne source/candidat plutôt qu'une superposition pixel-perfect avec l'UI UR2D2.

# G-S05 - Validation fonctionnelle

- **Experience :** G - Import du modele minimal de circuit depuis UR2D2
- **Scenario :** G-S05
- **Statut :** valide
- **Date :** 2026-07-29T17:11:41Z
- **Visualisation :** `C:\Users\jerem\Documents\UnityProject\Automation-LAP\prototypes\ur2d2-track-import\results\G_S05_FUNCTIONAL_VISUALIZATION.svg`

## Objectif

Charger le `TrackDefinition` converti en G-S03, le pretraiter avec les outils de C et faire parcourir plusieurs tours au controleur autonome C-S03 avec la QFC55.

## Donnees

- Piste importee : `prototypes/ur2d2-track-import/results/g_s03_track_definition_candidate.json`
- Vehicule : QFC55 - Magmort - Carcharhini RCZ
- Exporteur vehicule : `0.1.13-a9-steering-raw-graphs`
- Longueur importee : 272.884 m
- Largeur totale : 10.000 a 10.000 m
- Points de ligne centrale : 16

## Resultats

| dt | Tours | Duree | Tour 1 | Tour 2 | Tour 3 | Vitesse moy. | Vitesse max | Erreur lat. moy. | Erreur lat. max | Sorties | Stable |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0.01667 | 3 | 65.03 | 21.73 | 21.63 | 21.65 | 44.05 | 80.61 | 0.874 | 2.746 | 0 | oui |
| 0.00833 | 3 | 65.07 | 21.75 | 21.65 | 21.66 | 44.02 | 80.47 | 0.878 | 2.774 | 0 | oui |

## Comparaison canonique

- Longueur piste canonique C : 381.915 m
- Ecart de longueur : -28.55 %
- Temps 3 tours canonique : 83.33 s
- Temps 3 tours importe : 65.07 s
- Ecart temps : -21.92 %

## Lecture

- Le `TrackDefinition` importe passe le validateur C-S01 sans correction cachee.
- La QFC55 termine les tours demandes ; le run de reference compte 0 ticks hors piste.
- La comparaison avec la piste canonique sert uniquement de repere technique : la geometrie importee n'est pas censee avoir les memes performances.
- La visualisation superpose le contexte G-S04 et la trajectoire fonctionnelle coloree par vitesse pour confirmer le rendu.

G-S05 est validee fonctionnellement. Le rendu visuel final a ete confirme.

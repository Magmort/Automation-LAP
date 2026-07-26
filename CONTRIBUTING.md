# Contribuer à Automation LAP

Le projet est actuellement centré sur la préproduction, les expériences et la documentation. Une contribution doit rendre les décisions, hypothèses et résultats vérifiables.

## Flux de travail

1. Créer une issue ou identifier un élément du plan.
2. Créer une branche courte depuis `main`.
3. Modifier uniquement le périmètre annoncé.
4. Ajouter ou mettre à jour tests, mesures et documentation.
5. Ouvrir une pull request expliquant le changement et sa validation.
6. Fusionner après revue des impacts sur le plan et les ADR.

## Nommage des branches

- `docs/<sujet>` pour la documentation ;
- `experiment/<sujet>` pour un prototype de faisabilité ;
- `feature/<sujet>` pour une fonctionnalité ;
- `fix/<sujet>` pour une correction ;
- `agent/<sujet>` pour une branche préparée par un agent automatisé.

## Commits

Les messages sont courts, à l’impératif ou sous forme d’action claire. Une pull request peut contenir plusieurs commits lorsque cela facilite la revue, mais ne doit pas mélanger des sujets sans rapport.

## Documentation et décisions

- Le plan général décrit le cap et le périmètre.
- Une spécification décrit un système en détail.
- Un rapport de faisabilité décrit une expérience et ses résultats.
- Un ADR consigne une décision structurante et ses conséquences.

Ne pas présenter une hypothèse comme une décision validée. Les valeurs provisoires doivent être marquées comme telles.

## Prototypes

Un prototype de faisabilité peut être jetable. Il doit néanmoins fournir :

- une question précise ;
- une procédure reproductible ;
- des données d’entrée identifiables ;
- des métriques ;
- des critères de réussite ;
- une conclusion documentée.

Le passage d’un prototype au code de production exige une décision explicite.

## Code C#

Lors de l’introduction du code :

- activer les références nullables ;
- privilégier des types explicites et des unités non ambiguës ;
- éviter les dépendances Unity dans le cœur ;
- injecter l’horloge et les sources aléatoires lorsque nécessaire ;
- éviter les allocations dans les boucles fréquentes après mesure ;
- documenter les invariants physiques et conventions de coordonnées ;
- ajouter des tests reproductibles avec des graines fixes.

## Pull requests

Une pull request doit préciser :

- ce qui change ;
- pourquoi le changement est nécessaire ;
- les effets pour le projet ;
- les tests ou mesures effectués ;
- les documents ou ADR affectés ;
- les risques et suites éventuelles.

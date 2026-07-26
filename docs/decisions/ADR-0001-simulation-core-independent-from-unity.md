# ADR-0001 — Cœur de simulation indépendant de Unity

- **Statut :** proposé
- **Date :** 25 juillet 2026

## Contexte

Le projet utilise Unity pour le rendu 2D, les caméras et les interfaces. Il doit également exécuter des courses accélérées, réaliser des campagnes statistiques, automatiser des tests et relire des courses enregistrées.

Faire de la scène Unity ou de `Rigidbody2D` l’autorité de simulation rendrait ces besoins plus difficiles à tester, à reproduire et à faire évoluer.

## Décision

Le moteur de simulation sera développé sous forme de bibliothèques C# sans dépendance vers Unity. Il sera l’unique autorité pour les positions, vitesses, états mécaniques, décisions, règles et résultats.

Unity consommera des états de lecture et les interpolera pour l’affichage. Les types Unity ne seront pas utilisés dans les contrats publics du cœur.

## Conséquences positives

- simulation exécutable sans rendu ;
- tests unitaires et statistiques simplifiés ;
- contrôle explicite du pas de temps ;
- possibilité d’accélérer la simulation ;
- réduction du couplage avec une version de Unity ;
- replay et outils externes plus simples à construire.

## Coûts et contraintes

- nécessité d’écrire ou intégrer notre propre modèle physique ;
- couche d’adaptation entre le cœur et Unity ;
- synchronisation et interpolation à concevoir ;
- impossibilité d’utiliser directement certains composants Unity comme modèle métier.

## Alternatives écartées

- `Rigidbody2D` comme autorité principale ;
- logique de course répartie dans des `MonoBehaviour` ;
- simulation dépendante d’une scène Unity chargée.

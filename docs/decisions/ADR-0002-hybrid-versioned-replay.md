# ADR-0002 — Replay hybride et versionné

- **Statut :** proposé
- **Date :** 25 juillet 2026

## Contexte

Le projet doit permettre de revisionner une course et de naviguer dans sa chronologie. Une re-simulation reposant uniquement sur une graine aléatoire peut diverger après un changement de formule, de précision numérique, d’ordre d’exécution ou de version logicielle.

Enregistrer chaque valeur à chaque tick garantirait la lecture, mais produirait des fichiers inutilement volumineux.

## Décision

Le format de replay combinera :

- un en-tête versionné et les empreintes des définitions ;
- les graines et versions des modèles ;
- des images-clés périodiques ;
- des événements horodatés ;
- des canaux de télémétrie échantillonnés selon leur utilité.

La lecture vers un instant arbitraire partira d’une image-clé proche et appliquera les échantillons ou interpolations nécessaires. Le replay ne recalculera pas les décisions de l’IA comme source unique de vérité.

## Conséquences positives

- lecture stable malgré l’évolution de la simulation ;
- retour arrière et navigation temporelle ;
- événements directement indexables ;
- compromis réglable entre précision et taille ;
- données utilisables pour analyse et débogage.

## Coûts et contraintes

- schéma de fichier à versionner ;
- migrations ou refus explicite des formats incompatibles ;
- politique de fréquence et de compression à définir ;
- tests de fidélité nécessaires.

## Alternatives écartées

- re-simulation déterministe uniquement ;
- enregistrement vidéo ;
- capture exhaustive de tous les états à chaque tick.

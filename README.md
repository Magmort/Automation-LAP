# Automation LAP

Simulation automobile 2D vue du dessus dans laquelle toutes les voitures sont pilotées par des intelligences artificielles. Le projet vise à simuler une course complète — physique, trafic, stratégie, prise de risque, incidents et direction de course — puis à l’enregistrer afin de pouvoir la revisionner et l’analyser.

Les caractéristiques des voitures seront alimentées par des données exportées depuis **Automation - The Car Company Tycoon**, puis converties vers un modèle physique interne stable et versionné.

## État du projet

La **Phase 1 — Étude de faisabilité** est active. Aucun code de production ne doit être engagé avant la validation des briques critiques : import Automation, modèle physique, conduite IA, trafic, performances et replay.

Le travail courant est l’**Expérience A — Extraction Automation**. Elle doit prouver que trois voitures contrastées peuvent être exportées vers un format brut, versionné et reproductible.

- [Ticket directeur de la Phase 1](https://github.com/Magmort/Automation-LAP/issues/2)
- [Tableau de bord de la Phase 1](docs/feasibility/PHASE_1_STATUS.md)
- [Protocole de l’expérience A](docs/feasibility/experiments/A-AUTOMATION-EXTRACTION.md)
- [Rapport consolidé](docs/feasibility/FEASIBILITY_REPORT.md)

La source de vérité du projet reste le document [Plan général du projet](docs/PROJECT_PLAN.md).

## Objectifs principaux

- Simuler une course sans intervention directe du joueur sur les commandes des voitures.
- Donner à chaque pilote une personnalité, des compétences, une perception et une tolérance au risque propres.
- Représenter les performances et les limites mécaniques des voitures avec un modèle physique 2D crédible.
- Faire émerger des stratégies de pneus, carburant, rythme, arrêts et réaction aux événements.
- Afficher la course en 2D vue du dessus, avec vue globale et suivi d’une voiture.
- Enregistrer états, événements, décisions et télémétrie pour permettre une relecture fiable.
- Permettre à terme la simulation accélérée et l’exécution sans interface graphique.

## Principes structurants

1. Le moteur de simulation est indépendant de Unity.
2. Unity est une couche de présentation et d’interaction, pas l’autorité physique.
3. Les données Automation sont conservées brutes puis converties vers un format interne.
4. Les unités internes utilisent le système international.
5. Définitions immuables, états dynamiques et événements sont séparés.
6. L’IA est organisée en couches : stratégie, tactique et contrôle de conduite.
7. Le replay est hybride : images-clés, événements et télémétrie versionnés.
8. Les décisions majeures sont documentées dans des ADR.

## Documentation

- [Index de la documentation](docs/README.md)
- [Plan général du projet](docs/PROJECT_PLAN.md)
- [Architecture cible](docs/architecture/OVERVIEW.md)
- [Plan d’étude de faisabilité](docs/feasibility/FEASIBILITY_PLAN.md)
- [Tableau de bord de la Phase 1](docs/feasibility/PHASE_1_STATUS.md)
- [Décisions d’architecture](docs/decisions/README.md)
- [Guide de contribution](CONTRIBUTING.md)

## Périmètre du premier vertical slice

Le premier objectif jouable est une course unique comprenant un circuit, trois modèles de voitures importées, douze à vingt concurrents, des pilotes différenciés, consommation, usure, arrêts, dépassements, incidents simples, chronométrage, classement et replay navigable.

Le championnat complet, l’économie, le multijoueur, les dégâts visuels avancés, la météo complexe et l’apprentissage automatique sont explicitement hors périmètre initial.

## Organisation cible

```text
src/
  AutomationLAP.Core/
  AutomationLAP.Physics/
  AutomationLAP.AI/
  AutomationLAP.Strategy/
  AutomationLAP.Rules/
  AutomationLAP.Replay/
  AutomationLAP.Automation/
  AutomationLAP.Persistence/
  AutomationLAP.Unity/
  AutomationLAP.Editor/
tests/
docs/
prototypes/
```

Cette arborescence est une cible d’architecture. Les projets de production seront créés progressivement après validation de la faisabilité ; les expériences jetables appartiennent à `prototypes/`.
